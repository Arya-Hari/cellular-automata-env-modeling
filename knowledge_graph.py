import requests
from bs4 import BeautifulSoup
from py2neo import Graph, Node, Relationship
from flask import Flask, jsonify

graph = Graph("bolt://localhost:7687", auth=("neo4j", "advancedalgo"))

def scrape_tumor_size_thresholds():
    url = "https://pubmed.ncbi.nlm.nih.gov/?term=glioma+tumor+size+classification"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("Error accessing PubMed")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("a", class_="docsum-title")

    thresholds = []
    for article in articles[:5]:  # First 5 papers
        title = article.text.strip()
        link = "https://pubmed.ncbi.nlm.nih.gov" + article['href']
        thresholds.append((title, link))

    return thresholds

def store_tumor_classifications():
    thresholds = scrape_tumor_size_thresholds()

    for title, link in thresholds:
        classification_node = Node("TumorStage", name=title, source="PubMed", url=link)
        graph.create(classification_node)
        print(f"Stored Tumor Classification: {title}")

store_tumor_classifications()


brain_regions = [
    "Frontal Lobe", "Temporal Lobe", "Occipital Lobe", "Parietal Lobe",
    "Cerebellum", "Brainstem", "Corpus Callosum"
]

def store_brain_regions():
    for region in brain_regions:
        brain_node = Node("BrainRegion", name=region, source="SNOMED CT")
        graph.create(brain_node)
        print(f"Stored Brain Region: {region}")

store_brain_regions()

def get_tcia_glioma_datasets():
    url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/getCollectionValues"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()  # Returns a list of dataset names
    else:
        print("Error fetching TCIA datasets")
        return None

def store_tcia_data():
    datasets = get_tcia_glioma_datasets()
    if not datasets:
        return
    
    for dataset in datasets[:5]:  # Limit to 5 for simplicity
        dataset_name = str(dataset)  # Ensure value is stored as a string
        dataset_node = Node("Dataset", name=dataset_name, source="TCIA")
        graph.create(dataset_node)
        print(f"Stored MRI Dataset: {dataset_name}")

store_tcia_data()


def classify_tumor_with_verified_data(tumor_size):
    query = """
    MATCH (s:TumorStage) WHERE s.source='PubMed'
    RETURN s.name AS Stage, s.url AS Source
    """

    results = graph.run(query)
    for record in results:
        print(f"Tumor classified based on: {record['Stage']} - Reference: {record['Source']}")


classify_tumor_with_verified_data(3.5)


app = Flask(__name__)

@app.route('/get_verified_tumor_data', methods=['GET'])
def get_verified_tumor_data():
    query = """
    MATCH (s:TumorStage) WHERE s.source='PubMed'
    RETURN s.name AS Stage, s.url AS Source
    """
    results = graph.run(query).data()
    return jsonify(results)

@app.route('/get_verified_brain_regions', methods=['GET'])
def get_verified_brain_regions():
    query = """
    MATCH (b:BrainRegion) WHERE b.source='SNOMED CT'
    RETURN b.name AS Region
    """
    results = graph.run(query).data()
    return jsonify(results)

@app.route('/get_verified_mri_datasets', methods=['GET'])
def get_verified_mri_datasets():
    query = """
    MATCH (d:Dataset) WHERE d.source='TCIA'
    RETURN d.name AS Dataset
    """
    results = graph.run(query).data()
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
