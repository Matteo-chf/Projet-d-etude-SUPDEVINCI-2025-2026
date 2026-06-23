"""
Supprime de la collection `timeline` tous les documents qui n'ont pas
le label "reliable" ou "unreliable" (donc les "unknown" et les docs
pas encore traités par 5_label_sources.py).

A lancer apres 5_label_sources.py, pour ne garder en base que les
donnees utilisables pour l'entrainement (clustering K-Means).
"""

from mongo_service import MongoService

KEEP_LABELS = ["reliable", "unreliable"]


def run():
    mongo = MongoService()
    collection = mongo.db.timeline

    total = collection.count_documents({})
    to_delete = collection.count_documents({"source_label": {"$nin": KEEP_LABELS}})
    to_keep = total - to_delete

    print(f"Documents totaux       : {total}")
    print(f"A conserver (reliable/unreliable) : {to_keep}")
    print(f"A supprimer (unknown/non labelise) : {to_delete}")

    if to_delete == 0:
        print("Rien a supprimer.")
        return

    confirm = input(f"Confirmer la suppression de {to_delete} documents ? [y/N] ")
    if confirm.lower() != "y":
        print("Annule.")
        return

    result = collection.delete_many({"source_label": {"$nin": KEEP_LABELS}})
    print(f"Documents supprimes : {result.deleted_count}")


if __name__ == "__main__":
    run()
