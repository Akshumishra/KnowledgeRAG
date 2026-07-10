def get_documents_without_chunks(client):
    document_collection = client.collections.use("Document")
    chunk_collection = client.collections.use("DocumentChunk")

    documents = document_collection.query.fetch_objects(
        return_properties=["document_path"]
    )

    chunks = chunk_collection.query.fetch_objects(return_properties=["document_id"])

    chunked_ids = {obj.properties["document_id"] for obj in chunks.objects}

    return [
        {
            "document_id": str(doc.uuid),
            "document_path": doc.properties["document_path"],
        }
        for doc in documents.objects
        if str(doc.uuid) not in chunked_ids
    ]
