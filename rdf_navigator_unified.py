import streamlit as st
import pandas as pd
from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLStore
import requests
import io
import tempfile
import os
import re
from datetime import datetime

# --- Session State Initialization ---
if 'current_resource_uri' not in st.session_state:
    st.session_state.current_resource_uri = None
if 'navigation_history' not in st.session_state:
    st.session_state.navigation_history = []

# --- CSV to RDF Converter Logic (from csv_to_rdf_converter.py) ---
class CSVToRDFConverter:
    def __init__(self, namespace="http://example.org/dassault#", prefix="ex"):
        self.namespace = namespace
        self.prefix = prefix
    def clean_text(self, text):
        if pd.isna(text) or text is None:
            return ""
        text = str(text).strip()
        text = text.replace('\\', '\\\\').replace('"', '\\"')
        return text
    def format_date(self, date_str):
        if pd.isna(date_str) or not date_str:
            return ""
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
            try:
                date_obj = datetime.strptime(str(date_str), fmt)
                return date_obj.strftime('%d-%m-%Y')
            except ValueError:
                continue
        return str(date_str)
    def create_uri(self, entity_type, identifier):
        clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', str(identifier))
        return f"{self.prefix}:{entity_type}_{clean_id}"
    def write_prefixes(self, output):
        output.write(f"@prefix {self.prefix}: <{self.namespace}> .\n")
        output.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        output.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n")
    def is_date(self, val):
        if pd.isna(val) or not val:
            return False
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
            try:
                _ = datetime.strptime(str(val), fmt)
                return True
            except ValueError:
                continue
        return False
    def guess_entity_type(self, val):
        # Guess entity type from value pattern
        if isinstance(val, str):
            if val.startswith('IR_') or val.startswith('IR'):
                return 'IR'
            if val.startswith('ER_') or val.startswith('ER'):
                return 'ER'
            if val.startswith('Module_') or val.startswith('Module'):
                return 'Module'
            if val.startswith('Customer_') or val.startswith('Customer'):
                return 'Customer'
        return None
    def get_id_column(self, df):
        # Prefer first column ending with _ID, or named ER, IR, incident, enhancement
        for col in df.columns:
            if col.lower().endswith('_id'):
                return col
        for col in df.columns:
            if col.lower() in ['er', 'ir', 'incident', 'enhancement']:
                return col
        # Fallback: first column
        return df.columns[0]
    def convert_csvs_to_ttl(self, csv_files):
        output = io.StringIO()
        self.write_prefixes(output)
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                df.columns = [col.strip() for col in df.columns]
                id_col = self.get_id_column(df)
                for _, row in df.iterrows():
                    if pd.isna(row[id_col]) or not str(row[id_col]).strip():
                        continue
                    subj_val = str(row[id_col]).strip()
                    # Guess entity type from ID column name or value
                    entity_type = None
                    if id_col.lower().endswith('_id'):
                        entity_type = id_col[:-3].capitalize()
                    else:
                        entity_type = self.guess_entity_type(subj_val) or id_col.capitalize()
                    subj_uri = self.create_uri(entity_type, subj_val)
                    output.write(f"{subj_uri} a {self.prefix}:{entity_type} ;\n")
                    for col in df.columns:
                        if col == id_col or pd.isna(row[col]) or str(row[col]).strip() == '':
                            continue
                        pred = self.prefix + ":" + re.sub(r'[^a-zA-Z0-9_]', '_', col.strip())
                        val = row[col]
                        # Handle multi-valued fields
                        values = [v.strip() for v in str(val).split(',')] if isinstance(val, str) and ',' in str(val) else [val]
                        for v in values:
                            if pd.isna(v) or v == '':
                                continue
                            # If value looks like an entity, treat as object property
                            ent_type = self.guess_entity_type(v)
                            if ent_type:
                                obj_uri = self.create_uri(ent_type, v)
                                output.write(f"    {pred} {obj_uri} ;\n")
                            elif isinstance(v, str) and (v.startswith('http') or v.startswith('ex:')):
                                output.write(f"    {pred} {v} ;\n")
                            else:
                                # Guess datatype
                                if isinstance(v, (int, float)):
                                    dtype = '"' + str(v) + '"^^xsd:float' if isinstance(v, float) else '"' + str(v) + '"^^xsd:integer'
                                elif self.is_date(v):
                                    dtype = f'"{self.format_date(v)}"^^xsd:date'
                                else:
                                    dtype = f'"{self.clean_text(v)}"'
                                output.write(f"    {pred} {dtype} ;\n")
                    output.seek(output.tell() - 2)
                    output.write(" .\n\n")
            except Exception as e:
                continue
        return output.getvalue()

# --- Streamlit App ---
st.set_page_config(page_title="Unified RDF Navigator", layout="wide")
st.title("Unified RDF Navigator with Triple Store Integration")

# Sidebar: Triple Store Configuration
st.sidebar.header("Triple Store Configuration")
def_store_url = "http://localhost:3030/ds"
store_url = st.sidebar.text_input("Fuseki Base URL", value=def_store_url)
data_url = store_url.rstrip("/") + "/data"
sparql_url = store_url.rstrip("/") + "/sparql"
update_url = store_url.rstrip("/") + "/update"

# Sidebar: Data Management
st.sidebar.header("Data Management")
if st.sidebar.button("Clear All Data in Triple Store"):
    # Use SPARQL Update to clear all data
    clear_query = "CLEAR ALL"
    resp = requests.post(update_url, data={"update": clear_query})
    if resp.status_code == 200:
        st.sidebar.success("Triple store cleared!")
    else:
        st.sidebar.error(f"Failed to clear: {resp.text}")
if st.sidebar.button("Download All Data (TTL)"):
    # Download all data as Turtle
    headers = {"Accept": "text/turtle"}
    resp = requests.get(data_url, headers=headers)
    if resp.status_code == 200:
        st.sidebar.download_button(
            label="Download RDF Data (TTL)",
            data=resp.content,
            file_name="triplestore_data.ttl",
            mime="text/turtle"
        )
    else:
        st.sidebar.error(f"Failed to download: {resp.text}")

# --- CSV Upload and Conversion ---
st.header("Upload CSV(s) to Add Data to Triple Store")
uploaded_files = st.file_uploader(
    "Upload one or more CSV files", type=["csv"], accept_multiple_files=True
)
if uploaded_files:
    converter = CSVToRDFConverter()
    csv_buffers = [io.StringIO(f.read().decode("utf-8")) for f in uploaded_files]
    ttl_data = converter.convert_csvs_to_ttl(csv_buffers)
    st.code(ttl_data, language="turtle")
    # Upload to triple store
    resp = requests.post(data_url, data=ttl_data.encode("utf-8"), headers={"Content-Type": "text/turtle"})
    if resp.status_code in (200, 201, 204):
        st.success("RDF data uploaded to triple store!")
    else:
        st.error(f"Failed to upload RDF: {resp.text}")

# --- Data Source Selection ---
st.sidebar.header("Data Source")
data_source = st.sidebar.radio(
    "Choose data source for navigation:",
    ["Triple Store", "Local File"],
    index=0
)

# --- Local File Loader ---
local_graph = None
if data_source == "Local File":
    st.sidebar.subheader("Load RDF Turtle File")
    ttl_file = st.sidebar.file_uploader("Upload RDF Turtle (.ttl) file", type=["ttl"], key="ttl_file")
    if ttl_file is not None:
        ttl_content = ttl_file.read().decode("utf-8")
        local_graph = Graph()
        try:
            local_graph.parse(data=ttl_content, format="turtle")
            st.sidebar.success(f"Loaded {len(local_graph)} triples from file.")
        except Exception as e:
            st.sidebar.error(f"Error loading RDF: {e}")

# --- Connect to Triple Store for Navigation ---
@st.cache_resource(show_spinner=False)
def get_graph(sparql_url):
    store = SPARQLStore(sparql_url)
    g = Graph(store=store)
    return g
triplestore_graph = get_graph(sparql_url)

# --- Choose which graph to use for navigation/querying ---
if data_source == "Triple Store":
    nav_graph = triplestore_graph
    st.header("RDF Navigation & Querying (Triple Store)")
else:
    nav_graph = local_graph
    st.header("RDF Navigation & Querying (Local File)")

# --- Unified RDF Navigator Logic ---
from rdflib import URIRef

class RDFNavigator:
    def __init__(self, graph):
        self.graph = graph
        self.namespaces = {}
        # Extract namespaces if possible
        try:
            for prefix, namespace in self.graph.namespaces():
                self.namespaces[prefix] = namespace
        except Exception:
            pass
    def get_resource_triples(self, resource_uri):
        try:
            uri_ref = URIRef(resource_uri)
            triples = []
            for s, p, o in self.graph.triples((uri_ref, None, None)):
                triples.append(('subject', str(s), str(p), str(o)))
            for s, p, o in self.graph.triples((None, None, uri_ref)):
                triples.append(('object', str(s), str(p), str(o)))
            return triples
        except Exception as e:
            st.error(f"Error retrieving triples: {str(e)}")
            return []
    def execute_sparql(self, query):
        try:
            results = self.graph.query(query)
            return list(results), None
        except Exception as e:
            return [], str(e)
    def get_all_resources(self):
        resources = set()
        for s, p, o in self.graph:
            if isinstance(s, URIRef):
                resources.add(str(s))
            if isinstance(o, URIRef):
                resources.add(str(o))
        return sorted(list(resources))
    def shorten_uri(self, uri):
        for prefix, namespace in self.namespaces.items():
            if uri.startswith(str(namespace)):
                return f"{prefix}:{uri[len(str(namespace)):]}"
        return uri
    def expand_uri(self, uri):
        if ':' in uri and not uri.startswith('http'):
            try:
                prefix, local = uri.split(':', 1)
                if prefix in self.namespaces:
                    return str(self.namespaces[prefix]) + local
            except:
                pass
        return uri
    def find_resource_by_name(self, name_or_uri):
        expanded_uri = self.expand_uri(name_or_uri)
        if expanded_uri.startswith('http'):
            uri_ref = URIRef(expanded_uri)
            if (uri_ref, None, None) in self.graph or (None, None, uri_ref) in self.graph:
                return expanded_uri
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ex: <http://example.org/dassault#>
        SELECT DISTINCT ?resource WHERE {{
            {{ ?resource rdfs:label ?label . FILTER(LCASE(STR(?label)) = LCASE(\"{name_or_uri}\")) }}
            UNION {{ ?resource a ex:Customer . ?resource rdfs:label ?label . FILTER(LCASE(STR(?label)) = LCASE(\"{name_or_uri}\")) }}
            UNION {{ ?resource a ex:Module . ?resource rdfs:label ?label . FILTER(LCASE(STR(?label)) = LCASE(\"{name_or_uri}\")) }}
            UNION {{ ?resource a ex:IncidentReport . ?resource rdfs:label ?label . FILTER(LCASE(STR(?label)) = LCASE(\"{name_or_uri}\")) }}
            UNION {{ ?resource a ex:EnhancementRequest . ?resource ex:description ?label . FILTER(LCASE(STR(?label)) = LCASE(\"{name_or_uri}\")) }}
        }} LIMIT 1
        """
        results, error = self.execute_sparql(query)
        if results:
            return str(results[0][0])
        # Partial match
        query_partial = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ex: <http://example.org/dassault#>
        SELECT DISTINCT ?resource WHERE {{
            {{ ?resource rdfs:label ?label . FILTER(CONTAINS(LCASE(STR(?label)), LCASE(\"{name_or_uri}\"))) }}
            UNION {{ ?resource a ex:Customer . ?resource rdfs:label ?label . FILTER(CONTAINS(LCASE(STR(?label)), LCASE(\"{name_or_uri}\"))) }}
            UNION {{ ?resource a ex:Module . ?resource rdfs:label ?label . FILTER(CONTAINS(LCASE(STR(?label)), LCASE(\"{name_or_uri}\"))) }}
            UNION {{ ?resource a ex:IncidentReport . ?resource rdfs:label ?label . FILTER(CONTAINS(LCASE(STR(?label)), LCASE(\"{name_or_uri}\"))) }}
            UNION {{ ?resource a ex:EnhancementRequest . ?resource ex:description ?label . FILTER(CONTAINS(LCASE(STR(?label)), LCASE(\"{name_or_uri}\"))) }}
        }} LIMIT 1
        """
        results, error = self.execute_sparql(query_partial)
        if results:
            return str(results[0][0])
        return None
    def find_ir_er_by_id(self, ir_er_id):
        expanded_uri = self.expand_uri(ir_er_id)
        if expanded_uri.startswith('http'):
            uri_ref = URIRef(expanded_uri)
            if (uri_ref, None, None) in self.graph or (None, None, uri_ref) in self.graph:
                return expanded_uri
        query = f"""
        PREFIX ex: <http://example.org/dassault#>
        SELECT DISTINCT ?resource WHERE {{
            {{ ?resource a ex:IncidentReport . FILTER(STRENDS(STR(?resource), \"{ir_er_id}\")) }}
            UNION {{ ?resource a ex:EnhancementRequest . FILTER(STRENDS(STR(?resource), \"{ir_er_id}\")) }}
        }} LIMIT 1
        """
        results, error = self.execute_sparql(query)
        if results:
            return str(results[0][0])
        if not ir_er_id.startswith('ex:'):
            return self.find_ir_er_by_id(f"ex:{ir_er_id}")
        return None
    def get_node_description(self, node_uri):
        try:
            query = f"""
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?description ?label WHERE {{
                <{node_uri}> ex:description ?description .
                OPTIONAL {{ <{node_uri}> rdfs:label ?label }}
            }} LIMIT 1
            """
            results, error = self.execute_sparql(query)
            if results:
                description = str(results[0][0])
                label = str(results[0][1]) if results[0][1] else ""
                return f"{label}: {description}" if label else description
            query_label = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?label WHERE {{ <{node_uri}> rdfs:label ?label . }} LIMIT 1
            """
            results, error = self.execute_sparql(query_label)
            if results:
                return str(results[0][0])
            return None
        except:
            return None
    def find_connections(self, resource1, resource2):
        query = f"""
        SELECT DISTINCT ?connection_type ?path ?intermediate ?direction WHERE {{
            {{ <{resource1}> ?path <{resource2}> . BIND("direct" AS ?connection_type) BIND("forward" AS ?direction) BIND("none" AS ?intermediate) }}
            UNION {{ <{resource2}> ?path <{resource1}> . BIND("direct" AS ?connection_type) BIND("reverse" AS ?direction) BIND("none" AS ?intermediate) }}
            UNION {{ <{resource1}> ?p1 ?intermediate . ?intermediate ?p2 <{resource2}> . FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>) BIND("2-hop" AS ?connection_type) BIND("forward" AS ?direction) BIND(CONCAT(STR(?p1), " -> ", STR(?p2)) AS ?path) }}
            UNION {{ <{resource2}> ?p1 ?intermediate . ?intermediate ?p2 <{resource1}> . FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>) BIND("2-hop" AS ?connection_type) BIND("reverse" AS ?direction) BIND(CONCAT(STR(?p1), " -> ", STR(?p2)) AS ?path) }}
            UNION {{ <{resource1}> ?p1 ?intermediate . <{resource2}> ?p2 ?intermediate . FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>) FILTER(?p1 = ?p2) BIND("shared" AS ?connection_type) BIND("bidirectional" AS ?direction) BIND(STR(?p1) AS ?path) }}
            UNION {{ ?intermediate ?p1 <{resource1}> . ?intermediate ?p2 <{resource2}> . FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>) FILTER(?p1 = ?p2) BIND("inverse_shared" AS ?connection_type) BIND("bidirectional" AS ?direction) BIND(STR(?p1) AS ?path) }}
        }} ORDER BY ?connection_type ?direction
        """
        results, error = self.execute_sparql(query)
        return results, error

# --- Session State Initialization ---
if 'current_resource_uri' not in st.session_state:
    st.session_state.current_resource_uri = None
if 'navigation_history' not in st.session_state:
    st.session_state.navigation_history = []

# --- Main UI ---
st.markdown('<div class="main-header"><h1>RDF Navigator</h1><p>Explore and navigate RDF semantic data with powerful SPARQL queries</p></div>', unsafe_allow_html=True)

# --- Data Source Assignment ---
if nav_graph is None:
    st.info("Please upload an RDF Turtle (.ttl) file or select Triple Store to begin exploration")
    st.stop()

navigator = RDFNavigator(nav_graph)

# --- Tabs for different functionalities ---
tab1, tab2, tab3 = st.tabs(["Graph Explorer", "SPARQL Queries", "Graph Visualization"])

# --- Graph Explorer Tab (full UI from rdf_navigator.py) ---
with tab1:
    # Resource input section
    col1, col2 = st.columns([3, 1])
    with col1:
        resource_input = st.text_input(
            "Enter Resource URI",
            value=st.session_state.current_resource_uri or "",
            help="Enter a full URI or use namespace prefix (e.g., ex:IR001)",
            key="resource_input"
        )
    with col2:
        st.write("Or select:")
        if st.button("Random Resource"):
            resources = navigator.get_all_resources()
            if resources:
                import random
                random_resource = random.choice(resources)
                st.session_state.current_resource_uri = random_resource
                st.rerun()
    # Button to explore the entered resource
    if resource_input:
        if st.button("Explore Resource", key="explore_button"):
            expanded_uri = navigator.expand_uri(resource_input)
            st.session_state.current_resource_uri = expanded_uri
            st.rerun()
    # Resource dropdown (showing first 50 resources)
    resources = navigator.get_all_resources()[:50]
    if resources:
        selected_resource = st.selectbox(
            "Or select from available resources (first 50):",
            options=[""] + resources,
            format_func=lambda x: navigator.shorten_uri(x) if x else "Select a resource...",
            key="resource_dropdown"
        )
        if selected_resource and selected_resource != st.session_state.current_resource_uri:
            st.session_state.current_resource_uri = selected_resource
            st.rerun()
    # Display current resource information
    current_resource = st.session_state.current_resource_uri
    if current_resource:
        st.subheader(f"Resource Details: {navigator.shorten_uri(current_resource)}")
        st.code(current_resource, language="text")
        triples = navigator.get_resource_triples(current_resource)
        if triples:
            if current_resource not in st.session_state.navigation_history:
                st.session_state.navigation_history.append(current_resource)
            st.success(f"Found {len(triples)} triples for this resource")
            subjects = [t for t in triples if t[0] == 'subject']
            objects = [t for t in triples if t[0] == 'object']
            if subjects:
                st.subheader("As Subject (outgoing relationships)")
                for idx, (_, s, p, o) in enumerate(subjects):
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            st.write(f"**Property:** {navigator.shorten_uri(p)}")
                        with col2:
                            st.write(f"**Object:** {navigator.shorten_uri(o)}")
                        with col3:
                            try:
                                if o.startswith('http') and not o.startswith('http://www.w3.org/2001/XMLSchema#'):
                                    if st.button(f"Navigate to {navigator.shorten_uri(o)}", key=f"nav_obj_{idx}_{hash(o)}"):
                                        st.session_state.current_resource_uri = o
                                        st.rerun()
                            except:
                                pass
            if objects:
                st.subheader("As Object (incoming relationships)")
                for idx, (_, s, p, o) in enumerate(objects):
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            st.write(f"**Subject:** {navigator.shorten_uri(s)}")
                        with col2:
                            st.write(f"**Property:** {navigator.shorten_uri(p)}")
                        with col3:
                            try:
                                if s.startswith('http') and not s.startswith('http://www.w3.org/2001/XMLSchema#'):
                                    if st.button(f"Navigate to {navigator.shorten_uri(s)}", key=f"nav_subj_{idx}_{hash(s)}"):
                                        st.session_state.current_resource_uri = s
                                        st.rerun()
                            except:
                                pass
        else:
            st.warning("No triples found for this resource. Please check the URI or try a different resource.")
            if resources:
                st.info("Try one of these available resources:")
                for i, res in enumerate(resources[:5]):
                    st.text(f"• {navigator.shorten_uri(res)}")
    # Navigation history
    if st.session_state.navigation_history:
        st.header("Navigation History")
        for i, resource in enumerate(reversed(st.session_state.navigation_history[-5:])):
            if st.button(f"Back {navigator.shorten_uri(resource)}", key=f"nav_{i}"):
                st.session_state.current_resource_uri = resource
                st.rerun()

# --- SPARQL Queries Tab (full UI from rdf_navigator.py) ---
with tab2:
    st.header("SPARQL Query Tools")
    # Query Scenario 1: Find Link Between Two IRs/Functions/ERs
    st.markdown('<div class="query-card">', unsafe_allow_html=True)
    st.subheader("Query 1: Find Links Between Two IRs/Functions/ERs")
    col1, col2 = st.columns(2)
    with col1:
        resource1 = st.text_input("First IR/ER ID", key="q1_r1", help="Enter IR ID (e.g., 'IR_IR004') or ER ID (e.g., 'ER_ER004')")
    with col2:
        resource2 = st.text_input("Second IR/ER ID", key="q1_r2", help="Enter IR ID (e.g., 'IR_IR005') or ER ID (e.g., 'ER_ER005')")
    if st.button("Find Connections", key="q1_btn"):
        if resource1 and resource2:
            expanded_r1 = navigator.find_ir_er_by_id(resource1)
            expanded_r2 = navigator.find_ir_er_by_id(resource2)
            if not expanded_r1:
                st.error(f"IR/ER '{resource1}' not found. Try using ID like 'IR_IR004' or 'ER_ER004'.")
            elif not expanded_r2:
                st.error(f"IR/ER '{resource2}' not found. Try using ID like 'IR_IR005' or 'ER_ER005'.")
            else:
                results, error = navigator.find_connections(expanded_r1, expanded_r2)
                if error:
                    st.error(f"Query error: {error}")
                elif results:
                    st.success(f"Found {len(results)} connections between the resources")
                    connection_data = []
                    for result in results:
                        connection_type = str(result[0])
                        path = str(result[1])
                        intermediate = str(result[2])
                        direction = str(result[3])
                        if connection_type == "direct":
                            desc = f"Direct connection ({direction})"
                            detail = f"{navigator.shorten_uri(path)}"
                        elif connection_type == "2-hop":
                            desc = f"2-hop connection ({direction})"
                            detail = f"Via {navigator.shorten_uri(intermediate)}: {path}"
                        elif connection_type == "shared":
                            desc = f"Shared connection"
                            detail = f"Both connected to {navigator.shorten_uri(intermediate)} via {navigator.shorten_uri(path)}"
                        elif connection_type == "inverse_shared":
                            desc = f"Common source"
                            detail = f"{navigator.shorten_uri(intermediate)} connects to both via {navigator.shorten_uri(path)}"
                        else:
                            desc = connection_type
                            detail = path
                        connection_data.append({
                            "Connection Type": desc,
                            "Details": detail,
                            "Direction": direction,
                            "Intermediate/Property": navigator.shorten_uri(intermediate) if intermediate != "none" else "N/A"
                        })
                    df = pd.DataFrame(connection_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No connections found between these resources")
    st.markdown('</div>', unsafe_allow_html=True)

    # Query Scenario 2: Status of a Customer
    st.markdown('<div class="query-card">', unsafe_allow_html=True)
    st.subheader("Query 2: Customer Status")
    customer_name = st.text_input("Customer Name or URI", key="q2_customer", help="Enter customer name (e.g., 'Tesla') or URI (e.g., 'ex:Customer_Tesla')")
    if st.button("Get Customer Status", key="q2_btn"):
        if customer_name:
            expanded_customer = navigator.find_resource_by_name(customer_name)
            if not expanded_customer:
                st.error(f"Customer '{customer_name}' not found. Try using full URI or check spelling.")
            else:
                query = f"""
                PREFIX ex: <http://example.org/dassault#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT DISTINCT ?item ?type ?status ?title ?domain WHERE {{
                    ?item ex:belongsToCustomer <{expanded_customer}> .
                    ?item rdf:type ?type .
                    OPTIONAL {{ ?item ex:status ?status }}
                    OPTIONAL {{ ?item ex:description ?title }}
                    OPTIONAL {{ ?item ex:severity ?domain }}
                }}
                ORDER BY ?type ?item
                """
                results, error = navigator.execute_sparql(query)
                if error:
                    st.error(f"Query error: {error}")
                elif results:
                    df = pd.DataFrame(results, columns=['Item', 'Type', 'Status', 'Title', 'Domain'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No items found for this customer")
    st.markdown('</div>', unsafe_allow_html=True)

    # Query Scenario 3: Customers with Similar Requests
    st.markdown('<div class="query-card">', unsafe_allow_html=True)
    st.subheader("Query 3: Customers with Similar Requests")
    domain_filter = st.text_input(
        "Domain to search for",
        key="q3_domain",
        help="Enter a keyword (e.g., 'reporting') or full URI (e.g., 'http://example.org/dassault#Module_Reporting')"
    )
    if st.button("Find Similar Requests", key="q3_btn"):
        if domain_filter:
            expanded_filter = navigator.expand_uri(domain_filter)
            query = f"""
            PREFIX ex: <http://example.org/dassault#>
            SELECT DISTINCT ?customer ?item ?title ?domain WHERE {{
                ?item ex:belongsToCustomer ?customer .
                ?item ex:mentionsFunction ?domain .
                OPTIONAL {{ ?item ex:description ?title }}
                FILTER(
                    ?domain = <{domain_filter}> ||
                    ?domain = <{expanded_filter}> ||
                    CONTAINS(LCASE(STR(?domain)), LCASE("{domain_filter}")) ||
                    CONTAINS(LCASE(REPLACE(STR(?domain), "_", " ")), LCASE("{domain_filter}")) ||
                    CONTAINS(LCASE(REPLACE(REPLACE(STR(?domain), "^.*[/#]", ""), "_", " ")), LCASE("{domain_filter}"))
                )
            }}
            ORDER BY ?customer ?item
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    customer = navigator.shorten_uri(str(row[0]))
                    item = navigator.shorten_uri(str(row[1]))
                    title = str(row[2]) if row[2] else "No description"
                    domain = navigator.shorten_uri(str(row[3]))
                    data.append({
                        "Customer": customer,
                        "Item": item,
                        "Title": title,
                        "Domain": domain
                    })
                df = pd.DataFrame(data)
                st.success(f"Found {len(df)} items matching domain '{domain_filter}'")
                st.dataframe(df, use_container_width=True)
                unique_customers = df['Customer'].nunique()
                st.info(f"Summary: {unique_customers} unique customers with requests related to '{domain_filter}'")
                if expanded_filter != domain_filter:
                    st.info(f"Searched for: '{domain_filter}' (expanded to: {expanded_filter})")
                else:
                    st.info(f"Searched for: '{domain_filter}'")
            else:
                st.info(f"No requests found for domain '{domain_filter}'")
                st.warning("Try different domain names like 'security', 'reporting', 'authentication', etc.")
                debug_query = """
                PREFIX ex: <http://example.org/dassault#>
                SELECT DISTINCT ?domain WHERE {
                    ?item ex:mentionsFunction ?domain .
                }
                LIMIT 10
                """
                debug_results, debug_error = navigator.execute_sparql(debug_query)
                if not debug_error and debug_results:
                    st.info("Available domains in your data (first 10):")
                    for row in debug_results:
                        st.text(f"• {navigator.shorten_uri(str(row[0]))}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Query Scenario 4: Priority Analysis & Risk Assessment
    st.markdown('<div class="query-card">', unsafe_allow_html=True)
    st.subheader("Query 4: Priority Analysis & Risk Assessment")
    analysis_type = st.selectbox(
        "Select Analysis Type:",
        ["High Priority Incidents", "Module Risk Assessment", "Severity vs Domain Analysis"],
        key="q4_type"
    )
    if st.button("Analyze Priority & Risk", key="q4_btn"):
        if analysis_type == "High Priority Incidents":
            query = """
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?incident ?label ?customer ?severity ?priority ?module ?status WHERE {
                ?incident a ex:IncidentReport .
                ?incident rdfs:label ?label .
                ?incident ex:belongsToCustomer ?customer .
                ?incident ex:severity ?severity .
                ?incident ex:priority ?priority .
                ?incident ex:mentionsFunction ?module .
                ?incident ex:status ?status .
                FILTER(?priority IN ("P0", "P1"))
            }
            ORDER BY ?priority ?severity
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    data.append({
                        "Incident": navigator.shorten_uri(str(row[0])),
                        "Label": str(row[1]),
                        "Customer": navigator.shorten_uri(str(row[2])),
                        "Severity": str(row[3]),
                        "Priority": str(row[4]),
                        "Module": navigator.shorten_uri(str(row[5])),
                        "Status": str(row[6])
                    })
                df = pd.DataFrame(data)
                st.success(f"Found {len(df)} high-priority incidents")
                st.dataframe(df, use_container_width=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Critical (P0)", len(df[df['Priority'] == 'P0']))
                with col2:
                    st.metric("High (P1)", len(df[df['Priority'] == 'P1']))
                with col3:
                    st.metric("Open Issues", len(df[df['Status'] == 'Open']))
            else:
                st.info("No high-priority incidents found")
        elif analysis_type == "Module Risk Assessment":
            query = """
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?module ?moduleLabel ?incidentCount ?criticalCount ?highCount ?openCount WHERE {
                {
                    SELECT ?module (COUNT(?incident) AS ?incidentCount) 
                           (COUNT(IF(?priority = "P0", ?incident, ?dummy)) AS ?criticalCount)
                           (COUNT(IF(?priority = "P1", ?incident, ?dummy)) AS ?highCount)
                           (COUNT(IF(?status = "Open", ?incident, ?dummy)) AS ?openCount) WHERE {
                        ?incident a ex:IncidentReport .
                        ?incident ex:mentionsFunction ?module .
                        ?incident ex:priority ?priority .
                        ?incident ex:status ?status .
                        BIND("dummy" AS ?dummy)
                    }
                    GROUP BY ?module
                }
                ?module rdfs:label ?moduleLabel .
            }
            ORDER BY DESC(?incidentCount)
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    data.append({
                        "Module": navigator.shorten_uri(str(row[0])),
                        "Module Name": str(row[1]),
                        "Total Incidents": int(str(row[2])),
                        "Critical (P0)": int(str(row[3])),
                        "High (P1)": int(str(row[4])),
                        "Open Issues": int(str(row[5]))
                    })
                df = pd.DataFrame(data)
                st.success(f"Risk assessment for {len(df)} modules")
                st.dataframe(df, use_container_width=True)
                st.subheader("Module Risk Heatmap")
                risk_df = df.copy()
                risk_df['Risk Score'] = (risk_df['Critical (P0)'] * 3 + 
                                       risk_df['High (P1)'] * 2 + 
                                       risk_df['Open Issues'])
                st.dataframe(risk_df.sort_values('Risk Score', ascending=False), use_container_width=True)
            else:
                st.info("No module risk data found")
        elif analysis_type == "Severity vs Domain Analysis":
            query = """
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?domain ?severity (COUNT(?incident) AS ?incidentCount) WHERE {
                ?incident a ex:IncidentReport .
                ?incident ex:belongsToCustomer ?customer .
                ?incident ex:severity ?severity .
                ?customer ex:domain ?domain .
            }
            GROUP BY ?domain ?severity
            ORDER BY ?domain ?severity
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    data.append({
                        "Domain": str(row[0]),
                        "Severity": str(row[1]),
                        "Incident Count": int(str(row[2]))
                    })
                df = pd.DataFrame(data)
                st.success(f"Severity analysis across {df['Domain'].nunique()} domains")
                st.dataframe(df, use_container_width=True)
                pivot_df = df.pivot(index='Domain', columns='Severity', values='Incident Count').fillna(0)
                st.subheader("Severity Distribution by Domain")
                st.dataframe(pivot_df, use_container_width=True)
            else:
                st.info("No severity vs domain data found")
    st.markdown('</div>', unsafe_allow_html=True)

    # Query Scenario 5: Product Performance Analysis
    st.markdown('<div class="query-card">', unsafe_allow_html=True)
    st.subheader("Query 5: Product Performance Analysis")
    product_analysis = st.selectbox(
        "Select Product Analysis:",
        ["Product Incident Comparison", "Product Enhancement Analysis", "Product-Specific Patterns"],
        key="q5_type"
    )
    if st.button("Analyze Product Performance", key="q5_btn"):
        if product_analysis == "Product Incident Comparison":
            query = """
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?product ?incidentCount ?enhancementCount ?totalIssues WHERE {
                {
                    SELECT ?product (COUNT(?incident) AS ?incidentCount) WHERE {
                        ?incident a ex:IncidentReport .
                        ?incident ex:product ?product .
                    }
                    GROUP BY ?product
                }
                {
                    SELECT ?product (COUNT(?enhancement) AS ?enhancementCount) WHERE {
                        ?enhancement a ex:EnhancementRequest .
                        ?enhancement ex:product ?product .
                    }
                    GROUP BY ?product
                }
                BIND(?incidentCount + ?enhancementCount AS ?totalIssues)
            }
            ORDER BY DESC(?totalIssues)
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    data.append({
                        "Product": str(row[0]),
                        "Incidents": int(str(row[1])),
                        "Enhancements": int(str(row[2])),
                        "Total Issues": int(str(row[3]))
                    })
                df = pd.DataFrame(data)
                st.success(f"Product performance analysis for {len(df)} products")
                st.dataframe(df, use_container_width=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Incidents", df['Incidents'].sum())
                with col2:
                    st.metric("Total Enhancements", df['Enhancements'].sum())
                with col3:
                    st.metric("Most Issues", df.loc[df['Total Issues'].idxmax(), 'Product'])
            else:
                st.info("No product comparison data found")
        elif product_analysis == "Product Enhancement Analysis":
            query = """
            PREFIX ex: <http://example.org/dassault#>
            SELECT ?product ?requestType ?priority (COUNT(?enhancement) AS ?count) WHERE {
                ?enhancement a ex:EnhancementRequest .
                ?enhancement ex:product ?product .
                ?enhancement ex:requestType ?requestType .
                ?enhancement ex:priority ?priority .
            }
            GROUP BY ?product ?requestType ?priority
            ORDER BY ?product ?requestType ?priority
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    data.append({
                        "Product": str(row[0]),
                        "Request Type": str(row[1]),
                        "Priority": str(row[2]),
                        "Count": int(str(row[3]))
                    })
                df = pd.DataFrame(data)
                st.success(f"Enhancement analysis for {df['Product'].nunique()} products")
                st.dataframe(df, use_container_width=True)
                pivot_df = df.pivot_table(
                    index='Product', 
                    columns='Request Type', 
                    values='Count', 
                    aggfunc='sum'
                ).fillna(0)
                st.subheader("Enhancement Request Types by Product")
                st.dataframe(pivot_df, use_container_width=True)
            else:
                st.info("No product enhancement data found")
        elif product_analysis == "Product-Specific Patterns":
            query = """
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?product ?module ?moduleLabel ?incidentCount ?enhancementCount WHERE {
                {
                    SELECT ?product ?module (COUNT(?incident) AS ?incidentCount) WHERE {
                        ?incident a ex:IncidentReport .
                        ?incident ex:product ?product .
                        ?incident ex:mentionsFunction ?module .
                    }
                    GROUP BY ?product ?module
                }
                {
                    SELECT ?product ?module (COUNT(?enhancement) AS ?enhancementCount) WHERE {
                        ?enhancement a ex:EnhancementRequest .
                        ?enhancement ex:product ?product .
                        ?enhancement ex:mentionsFunction ?module .
                    }
                    GROUP BY ?product ?module
                }
                ?module rdfs:label ?moduleLabel .
            }
            ORDER BY ?product ?module
            """
            results, error = navigator.execute_sparql(query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                data = []
                for row in results:
                    data.append({
                        "Product": str(row[0]),
                        "Module": navigator.shorten_uri(str(row[1])),
                        "Module Name": str(row[2]),
                        "Incidents": int(str(row[3])),
                        "Enhancements": int(str(row[4]))
                    })
                df = pd.DataFrame(data)
                st.success(f"Product-module patterns for {df['Product'].nunique()} products")
                st.dataframe(df, use_container_width=True)
                st.subheader("Top Modules by Issues per Product")
                df['Total Issues'] = df['Incidents'] + df['Enhancements']
                top_modules = df.loc[df.groupby('Product')['Total Issues'].idxmax()]
                st.dataframe(top_modules[['Product', 'Module Name', 'Incidents', 'Enhancements', 'Total Issues']], use_container_width=True)
            else:
                st.info("No product-specific pattern data found")
    st.markdown('</div>', unsafe_allow_html=True)

    # Custom SPARQL Query
    st.subheader("Custom SPARQL Query")
    custom_query = st.text_area(
        "Enter your SPARQL query:",
        height=150,
        placeholder="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
    )
    if st.button("Execute Custom Query"):
        if custom_query:
            results, error = navigator.execute_sparql(custom_query)
            if error:
                st.error(f"Query error: {error}")
            elif results:
                if results:
                    columns = [str(var) for var in results[0]]
                    data = [[str(binding) for binding in row] for row in results]
                    df = pd.DataFrame(data, columns=columns)
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("Query returned no results")

# --- Graph Visualization Tab (full UI from rdf_navigator.py) ---
with tab3:
    st.header("Graph Visualization")
    if st.session_state.current_resource_uri:
        st.subheader(f"Visualizing connections for: {navigator.shorten_uri(st.session_state.current_resource_uri)}")
        from pyvis.network import Network
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
        current_uri = st.session_state.current_resource_uri
        net.add_node(current_uri, label=navigator.shorten_uri(current_uri), color="#ff6b6b", size=25)
        triples = navigator.get_resource_triples(current_uri)
        added_nodes = {current_uri}
        node_descriptions = {}
        for triple_type, s, p, o in triples[:20]:
            if triple_type == 'subject':
                if o not in added_nodes:
                    description = navigator.get_node_description(o)
                    node_descriptions[o] = description
                    node_color = "#4ecdc4"
                    if "IR_" in str(o):
                        node_color = "#ff7675"
                    elif "ER_" in str(o):
                        node_color = "#74b9ff"
                    elif "Module_" in str(o):
                        node_color = "#55a3ff"
                    elif "Customer_" in str(o):
                        node_color = "#00b894"
                    net.add_node(o, label=navigator.shorten_uri(o), color=node_color, size=15)
                    added_nodes.add(o)
                net.add_edge(s, o, label=navigator.shorten_uri(p), color="#95a5a6")
            else:
                if s not in added_nodes:
                    description = navigator.get_node_description(s)
                    node_descriptions[s] = description
                    node_color = "#45b7d1"
                    if "IR_" in str(s):
                        node_color = "#ff7675"
                    elif "ER_" in str(s):
                        node_color = "#74b9ff"
                    elif "Module_" in str(s):
                        node_color = "#55a3ff"
                    elif "Customer_" in str(s):
                        node_color = "#00b894"
                    net.add_node(s, label=navigator.shorten_uri(s), color=node_color, size=15)
                    added_nodes.add(s)
                net.add_edge(s, o, label=navigator.shorten_uri(p), color="#95a5a6")
        try:
            net.set_options("""
            var options = {
                "physics": {
                    "enabled": true,
                    "stabilization": {"iterations": 100}
                }
            }
            """)
            tmp_file = None
            try:
                tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html')
                net.save_graph(tmp_file.name)
                tmp_file.close()
                with open(tmp_file.name, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                custom_js = '''
                <script>
                function setupNodeClick() {
                    var network = window.network;
                    if (!network) {
                        setTimeout(setupNodeClick, 200);
                        return;
                    }
                    network.on('click', function(params) {
                        if(params.nodes.length > 0) {
                            var nodeId = params.nodes[0];
                            window.parent.postMessage({type: 'node_click', nodeId: nodeId}, '*');
                        }
                    });
                }
                setupNodeClick();
                window.addEventListener('message', (event) => {
                    if(event.data && event.data.type === 'set_resource') {
                    }
                });
                </script>
                '''
                html_content = html_content.replace('</body>', custom_js + '</body>')
                st.markdown('''<script>
                window.addEventListener('message', (event) => {
                    if(event.data && event.data.type === 'node_click') {
                        const nodeId = event.data.nodeId;
                        const input = window.parent.document.querySelector('input[data-testid="stNodeClick"]');
                        if(input) {
                            input.value = nodeId;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                });
                </script>''', unsafe_allow_html=True)
                node_click = st.text_input('','',key='stNodeClick',label_visibility='collapsed')
                if node_click:
                    st.session_state.current_resource_uri = node_click
                    st.rerun()
                st.components.v1.html(html_content, height=600)
                if node_descriptions:
                    st.subheader("Node Descriptions")
                    st.info("Click on nodes in the graph above to see their details. Below are descriptions of connected nodes:")
                    ir_descriptions = {k: v for k, v in node_descriptions.items() if v and "IR_" in str(k)}
                    er_descriptions = {k: v for k, v in node_descriptions.items() if v and "ER_" in str(k)}
                    module_descriptions = {k: v for k, v in node_descriptions.items() if v and "Module_" in str(k)}
                    customer_descriptions = {k: v for k, v in node_descriptions.items() if v and "Customer_" in str(k)}
                    if ir_descriptions:
                        st.markdown("**Incident Reports (IRs):**")
                        for node, desc in ir_descriptions.items():
                            with st.expander(f"{navigator.shorten_uri(node)}"):
                                st.write(desc)
                    if er_descriptions:
                        st.markdown("**Enhancement Requests (ERs):**")
                        for node, desc in er_descriptions.items():
                            with st.expander(f"{navigator.shorten_uri(node)}"):
                                st.write(desc)
                    if module_descriptions:
                        st.markdown("**Modules:**")
                        for node, desc in module_descriptions.items():
                            with st.expander(f"{navigator.shorten_uri(node)}"):
                                st.write(desc if desc else "Module information")
                    if customer_descriptions:
                        st.markdown("**Customers:**")
                        for node, desc in customer_descriptions.items():
                            with st.expander(f"{navigator.shorten_uri(node)}"):
                                st.write(desc if desc else "Customer information")
            except Exception as e:
                st.error(f"Error generating visualization: {str(e)}")
            finally:
                if tmp_file and os.path.exists(tmp_file.name):
                    try:
                        os.unlink(tmp_file.name)
                    except:
                        pass
        except Exception as e:
            st.error(f"Error generating visualization: {str(e)}")
    else:
        st.info("Navigate to a resource in the Graph Explorer to see its visualization")

# --- Session State Management ---
@st.cache_data(show_spinner=False)
def current_resource_uri(uri):
    st.session_state.current_resource_uri = uri
    st.session_state.navigation_history.append(uri)
    return uri

st.info("All data and queries are now persistent and shared via the triple store, or private via local file. Upload more CSVs to add more data to the triple store!") 