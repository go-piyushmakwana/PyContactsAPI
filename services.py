from bson.objectid import ObjectId
import bcrypt
import datetime
from database import (
    accounts_collection,
    user_contacts_collection,
    labels_collection,
    trash_collection
)

# --- User Services ---


async def check_user_async(username: str) -> bool:
    try:
        return await accounts_collection.find_one({"Username": username}) is not None
    except Exception as e:
        print(f"Error while checking username: {e}")
        return False


async def create_user_async(image: str, name: str, username: str, password: str, mobile: str):
    try:
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
        user = {
            "Photo": image, "Name": name, "Username": username,
            "Password": hashed_password, "Contact": mobile
        }
        await accounts_collection.insert_one(user)
        return True, "User created successfully."
    except Exception as e:
        print(f"Error while creating user: {e}")
        return False, "An error occurred while creating the user."


async def validate_user_async(username: str, password: str) -> bool:
    try:
        user = await accounts_collection.find_one({"Username": username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['Password']):
            return True
        return False
    except Exception as e:
        print(f"Error while validating user: {e}")
        return False


async def get_user_profile_async(username: str):
    try:
        return await accounts_collection.find_one({"Username": username})
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return None


async def update_user_async(username: str, image: str, name: str, mobile: str):
    try:
        update_fields = {"Name": name}
        if mobile:
            update_fields["Contact"] = mobile
        if image:
            update_fields["Photo"] = image
        result = await accounts_collection.update_one({"Username": username}, {"$set": update_fields})
        return result.modified_count == 1, "Profile updated successfully." if result.modified_count else "User not found or no changes made."
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return False, "An unexpected error occurred while updating the profile."


# --- Contact Services ---
async def get_contacts_async(username: str):
    try:
        user_contacts = await user_contacts_collection.find_one({"Username": username})
        return user_contacts.get("Contacts", []) if user_contacts else []
    except Exception as e:
        print(f"Error getting contacts: {e}")
        return []


async def get_contact_by_id_async(username: str, contact_id: str):
    try:
        obj_id = ObjectId(contact_id)
        user_contacts = await user_contacts_collection.find_one({"Username": username})
        if user_contacts:
            for contact in user_contacts.get("Contacts", []):
                if contact.get("_id") == obj_id:
                    return contact
        return None
    except Exception as e:
        print(f"Error getting contact: {e}")
        return None


async def add_contact_async(username, image, name, mobile, email, job_title, company, labels, dt):
    try:
        new_contact = {
            "_id": ObjectId(), "Photo": image, "Name": name, "Contact": mobile,
            "Email": email, "Job": job_title, "Company": company,
            "Labels": labels, "DateTime": dt
        }
        await user_contacts_collection.update_one(
            {"Username": username},
            {"$push": {"Contacts": new_contact}},
            upsert=True
        )
        return True, "Contact added successfully.", new_contact
    except Exception as e:
        print(f"Error adding contact: {e}")
        return False, "An error occurred while adding the contact.", None


async def update_contact_async(username, contact_id, new_name, mobile, email, job_title, company, labels):
    try:
        obj_id = ObjectId(contact_id)
        update_fields = {
            "Contacts.$.Name": new_name, "Contacts.$.Contact": mobile, "Contacts.$.Email": email,
            "Contacts.$.Job": job_title, "Contacts.$.Company": company, "Contacts.$.Labels": labels
        }
        result = await user_contacts_collection.update_one(
            {"Username": username, "Contacts._id": obj_id}, {"$set": update_fields}
        )
        return result.modified_count == 1, "Contact updated successfully." if result.modified_count else "Contact not found or no changes made."
    except Exception as e:
        print(f"Error updating contact: {e}")
        return False, "An error occurred while updating the contact."


async def move_to_trash_async(username: str, contact_id: str):
    try:
        obj_id = ObjectId(contact_id)
    except Exception:
        return False, "Invalid contact ID format."
    try:
        user_doc = await user_contacts_collection.find_one({"Username": username})
        if not user_doc:
            return False, "User not found."

        contact_to_move = next((c for c in user_doc.get(
            "Contacts", []) if c.get("_id") == obj_id), None)
        if not contact_to_move:
            return False, "Contact not found in main list."

        trash_item = {
            "contact_id": obj_id, "Username": username,
            "ContactDetails": contact_to_move, "deleted_at": datetime.datetime.utcnow()
        }
        await trash_collection.insert_one(trash_item)
        await user_contacts_collection.update_one({"Username": username}, {"$pull": {"Contacts": {"_id": obj_id}}})
        return True, "Contact moved to trash successfully."
    except Exception as e:
        print(f"Error moving contact to trash: {e}")
        return False, "An error occurred while moving the contact to trash."


async def merge_contacts_async(username: str, contact_ids: list):
    if not isinstance(contact_ids, list) or len(contact_ids) < 2:
        return False, "A list of at least two contact IDs is required to merge.", None

    merged_data = {"Labels": set()}
    contacts_to_delete_ids = []

    for cid in contact_ids:
        contact_id_str = str(cid.get('_id')) if isinstance(
            cid, dict) else str(cid)
        try:
            contact = await get_contact_by_id_async(username, contact_id_str)
            if not contact:
                return False, f"Contact with ID '{contact_id_str}' not found.", None

            contacts_to_delete_ids.append(contact.get("_id"))

            for key, value in contact.items():
                if key not in merged_data and value:
                    merged_data[key] = value
                if key == "Labels" and value:
                    merged_data["Labels"].update(value)
        except Exception:
            return False, f"Invalid contact ID format: '{contact_id_str}'", None

    # Remove non-data fields
    merged_data.pop("_id", None)

    success, message, new_contact = await add_contact_async(
        username,
        merged_data.get("Photo"), merged_data.get(
            "Name"), merged_data.get("Contact"),
        merged_data.get("Email"), merged_data.get(
            "Job"), merged_data.get("Company"),
        list(merged_data["Labels"]), datetime.datetime.now(
            datetime.timezone.utc).isoformat()
    )

    if success:
        await user_contacts_collection.update_one(
            {"Username": username},
            {"$pull": {"Contacts": {"_id": {"$in": contacts_to_delete_ids}}}}
        )
        if new_contact and '_id' in new_contact:
            new_contact['_id'] = str(new_contact['_id'])
        return True, "Contacts merged successfully.", new_contact
    else:
        return False, message, None


async def search_contacts_async(username: str, query: str):
    try:
        contacts = await get_contacts_async(username)
        q = query.lower()
        return [c for c in contacts if q in c.get("Name", "").lower() or q in c.get("Contact", "").lower() or q in c.get("Email", "").lower() or any(q in label.lower() for label in c.get("Labels", []))]
    except Exception as e:
        print(f"Error searching contacts: {e}")
        return []

# --- Trash Services ---


async def get_trashed_contacts_async(username: str):
    try:
        trashed_docs = []
        async for doc in trash_collection.find({"Username": username}).sort("deleted_at", -1):
            doc['_id'] = str(doc['_id'])
            doc['contact_id'] = str(doc['contact_id'])
            if 'ContactDetails' in doc and '_id' in doc['ContactDetails']:
                doc['ContactDetails']['_id'] = str(
                    doc['ContactDetails']['_id'])
            trashed_docs.append(doc)
        return trashed_docs
    except Exception as e:
        print(f"Error getting trashed contacts: {e}")
        return []


async def restore_contact_async(username, contact_id):
    try:
        obj_id = ObjectId(contact_id)
        trashed_item = await trash_collection.find_one_and_delete({"Username": username, "contact_id": obj_id})
        if not trashed_item:
            return False, "Contact not found in trash."

        await user_contacts_collection.update_one(
            {"Username": username}, {
                "$push": {"Contacts": trashed_item['ContactDetails']}}
        )
        return True, "Contact restored successfully."
    except Exception as e:
        print(f"Error restoring contact: {e}")
        return False, "An error occurred while restoring the contact."


async def delete_permanently_async(username: str, contact_id: str):
    try:
        obj_id = ObjectId(contact_id)
        result = await trash_collection.delete_one({"contact_id": obj_id, "Username": username})
        return result.deleted_count > 0, "Contact permanently deleted." if result.deleted_count else "Contact not found in trash."
    except Exception as e:
        print(f"Error deleting contact permanently: {e}")
        return False, "An error occurred while deleting the contact."


async def empty_trash_async(username: str):
    try:
        await trash_collection.delete_many({"Username": username})
        return True, "Trash emptied successfully."
    except Exception as e:
        print(f"Error emptying trash: {e}")
        return False, "An error occurred while emptying the trash."

# --- Label Services ---


async def create_label_async(username: str, label_name: str):
    try:
        await labels_collection.insert_one({"Username": username, "LabelName": label_name})
        return True, "Label created successfully."
    except Exception as e:
        print(f"Error creating label: {e}")
        return False, "An error occurred while creating the label."


async def get_labels_async(username: str):
    try:
        cursor = labels_collection.find({"Username": username})
        return [label["LabelName"] async for label in cursor]
    except Exception as e:
        print(f"Error getting labels: {e}")
        return []


async def delete_label_async(username: str, label_name: str):
    try:
        result = await labels_collection.delete_one({"Username": username, "LabelName": label_name})
        return result.deleted_count == 1, "Label deleted successfully." if result.deleted_count else "Label not found."
    except Exception as e:
        print(f"Error deleting label: {e}")
        return False, "An error occurred while deleting the label."


async def edit_the_label_async(username: str, old_label_name: str, new_label_name: str):
    try:
        result = await labels_collection.update_one(
            {"Username": username, "LabelName": old_label_name},
            {"$set": {"LabelName": new_label_name}}
        )
        return result.modified_count == 1, "Label updated successfully." if result.modified_count else "Label not found or no changes made."
    except Exception as e:
        print(f"Error updating label: {e}")
        return False, "An error occurred while updating the label."


async def check_the_label_exists_async(username: str, label_name: str):
    try:
        return await labels_collection.find_one({"Username": username, "LabelName": label_name}) is not None
    except Exception as e:
        print(f"Error checking label existence: {e}")
        return False
