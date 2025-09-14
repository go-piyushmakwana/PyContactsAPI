from quart import Quart
from quart_cors import cors
from config import config
from routes import api as api_blueprint
from database import helplines_collection

def create_app():
    """
    Application factory function to create and configure the Quart app.
    """
    app = Quart(__name__)

    # Load configuration
    app.config.from_object(config)

    # Setup CORS
    cors(
        app,
        allow_credentials=True,
        allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_origin="https://pycontacts.onrender.com/"  # Consider making this configurable
    )

    # Register Blueprints (routes)
    app.register_blueprint(api_blueprint)

    @app.before_serving
    async def initialize_db():
        """Seed the database with initial helpline contacts if it's empty."""
        try:
            if await helplines_collection.count_documents({}) == 0:
                print("Database is empty. Seeding with initial contacts...")
                await helplines_collection.insert_many([
                    {"_id": "0000100", "Name": "Police", "Contact": "100"},
                    {"_id": "0000108", "Name": "Ambulance", "Contact": "108"},
                    {"_id": "0000101", "Name": "Fire Department", "Contact": "101"},
                    {"_id": "00001098", "Name": "Child Helpline", "Contact": "1098"},
                    {"_id": "00001077", "Name": "Disaster Management", "Contact": "1077"}
                ])
                print("Seeding complete.")
            else:
                print("Database already contains helpline data.")
        except Exception as e:
            print(f"Error during database initialization: {e}")

    return app

if __name__ == "__main__":
    app = create_app()
    # For production, you would use a proper ASGI server like Hypercorn
    # hypercorn main:app
    app.run(debug=True)
