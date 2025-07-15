import streamlit as st
import pandas as pd
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS
import networkx as nx
from pyvis.network import Network
import tempfile
import os
from urllib.parse import urlparse
import re

# Page configuration
st.set_page_config(
    page_title="RDF Navigator",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .query-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .resource-card {
        background: #fff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .triple-row {
        background: #f8f9fa;
        padding: 0.5rem;
        margin: 0.2rem 0;
        border-radius: 4px;
        border-left: 3px solid #28a745;
    }
    .clickable-uri {
        color: #007bff;
        cursor: pointer;
        text-decoration: underline;
    }
    .clickable-uri:hover {
        color: #0056b3;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'rdf_graph' not in st.session_state:
    st.session_state.rdf_graph = None
if 'current_resource' not in st.session_state:
    st.session_state.current_resource = None
if 'navigation_history' not in st.session_state:
    st.session_state.navigation_history = []

class RDFNavigator:
    def __init__(self):
        self.graph = Graph()
        self.namespaces = {}
        
    def load_ttl_file(self, file_content):
        """Load RDF Turtle file content into the graph"""
        try:
            self.graph.parse(data=file_content, format='turtle')
            # Extract namespaces
            for prefix, namespace in self.graph.namespaces():
                self.namespaces[prefix] = namespace
            return True, f"Successfully loaded {len(self.graph)} triples"
        except Exception as e:
            return False, f"Error loading RDF file: {str(e)}"
    
    def get_resource_triples(self, resource_uri):
        """Get all triples where the resource is subject or object"""
        try:
            uri_ref = URIRef(resource_uri)
            triples = []
            
            # Get triples where resource is subject
            for s, p, o in self.graph.triples((uri_ref, None, None)):
                triples.append(('subject', str(s), str(p), str(o)))
            
            # Get triples where resource is object
            for s, p, o in self.graph.triples((None, None, uri_ref)):
                triples.append(('object', str(s), str(p), str(o)))
            
            return triples
        except Exception as e:
            st.error(f"Error retrieving triples: {str(e)}")
            return []
    
    def execute_sparql(self, query):
        """Execute SPARQL query and return results"""
        try:
            results = self.graph.query(query)
            return list(results), None
        except Exception as e:
            return [], str(e)
    
    def get_all_resources(self):
        """Get all unique resources in the graph"""
        resources = set()
        for s, p, o in self.graph:
            if isinstance(s, URIRef):
                resources.add(str(s))
            if isinstance(o, URIRef):
                resources.add(str(o))
        return sorted(list(resources))
    
    def shorten_uri(self, uri):
        """Shorten URI using known namespaces"""
        for prefix, namespace in self.namespaces.items():
            if uri.startswith(str(namespace)):
                return f"{prefix}:{uri[len(str(namespace)):]}"
        return uri
    
    def expand_uri(self, uri):
        """Expand prefixed URI to full URI"""
        if ':' in uri and not uri.startswith('http'):
            try:
                prefix, local = uri.split(':', 1)
                if prefix in self.namespaces:
                    return str(self.namespaces[prefix]) + local
            except:
                pass
        return uri
    
    def find_resource_by_name(self, name_or_uri):
        """Find resource by name or URI, handling both cases"""
        # First try to expand as URI
        expanded_uri = self.expand_uri(name_or_uri)
        
        # Check if the expanded URI exists in the graph
        if expanded_uri.startswith('http'):
            uri_ref = URIRef(expanded_uri)
            if (uri_ref, None, None) in self.graph or (None, None, uri_ref) in self.graph:
                return expanded_uri
        
        # If not found as URI, try to find by name/label
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ex: <http://example.org/dassault#>
        
        SELECT DISTINCT ?resource WHERE {{
            {{
                ?resource rdfs:label ?label .
                FILTER(LCASE(STR(?label)) = LCASE("{name_or_uri}"))
            }}
            UNION
            {{
                ?resource a ex:Customer .
                ?resource rdfs:label ?label .
                FILTER(LCASE(STR(?label)) = LCASE("{name_or_uri}"))
            }}
            UNION
            {{
                ?resource a ex:Module .
                ?resource rdfs:label ?label .
                FILTER(LCASE(STR(?label)) = LCASE("{name_or_uri}"))
            }}
            UNION
            {{
                ?resource a ex:IncidentReport .
                ?resource rdfs:label ?label .
                FILTER(LCASE(STR(?label)) = LCASE("{name_or_uri}"))
            }}
            UNION
            {{
                ?resource a ex:EnhancementRequest .
                ?resource ex:description ?label .
                FILTER(LCASE(STR(?label)) = LCASE("{name_or_uri}"))
            }}
        }}
        LIMIT 1
        """
        
        results, error = self.execute_sparql(query)
        if results:
            return str(results[0][0])
        
        # If still not found, try partial matching
        query_partial = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ex: <http://example.org/dassault#>
        
        SELECT DISTINCT ?resource WHERE {{
            {{
                ?resource rdfs:label ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{name_or_uri}")))
            }}
            UNION
            {{
                ?resource a ex:Customer .
                ?resource rdfs:label ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{name_or_uri}")))
            }}
            UNION
            {{
                ?resource a ex:Module .
                ?resource rdfs:label ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{name_or_uri}")))
            }}
            UNION
            {{
                ?resource a ex:IncidentReport .
                ?resource rdfs:label ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{name_or_uri}")))
            }}
            UNION
            {{
                ?resource a ex:EnhancementRequest .
                ?resource ex:description ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{name_or_uri}")))
            }}
        }}
        LIMIT 1
        """
        
        results, error = self.execute_sparql(query_partial)
        if results:
            return str(results[0][0])
        
        return None
    
    def find_ir_er_by_id(self, ir_er_id):
        """Find IR or ER by ID (e.g., IR_IR004, ER_ER004)"""
        # First try to expand as URI
        expanded_uri = self.expand_uri(ir_er_id)
        
        # Check if the expanded URI exists in the graph
        if expanded_uri.startswith('http'):
            uri_ref = URIRef(expanded_uri)
            if (uri_ref, None, None) in self.graph or (None, None, uri_ref) in self.graph:
                return expanded_uri
        
        # If not found as URI, try to find by ID pattern
        query = f"""
        PREFIX ex: <http://example.org/dassault#>
        
        SELECT DISTINCT ?resource WHERE {{
            {{
                ?resource a ex:IncidentReport .
                FILTER(STRENDS(STR(?resource), "{ir_er_id}"))
            }}
            UNION
            {{
                ?resource a ex:EnhancementRequest .
                FILTER(STRENDS(STR(?resource), "{ir_er_id}"))
            }}
        }}
        LIMIT 1
        """
        
        results, error = self.execute_sparql(query)
        if results:
            return str(results[0][0])
        
        # If still not found, try with ex: prefix
        if not ir_er_id.startswith('ex:'):
            return self.find_ir_er_by_id(f"ex:{ir_er_id}")
        
        return None
    
    def get_node_description(self, node_uri):
        """Get description for IR/ER nodes"""
        try:
            query = f"""
            PREFIX ex: <http://example.org/dassault#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?description ?label WHERE {{
                <{node_uri}> ex:description ?description .
                OPTIONAL {{ <{node_uri}> rdfs:label ?label }}
            }}
            LIMIT 1
            """
            
            results, error = self.execute_sparql(query)
            if results:
                description = str(results[0][0])
                label = str(results[0][1]) if results[0][1] else ""
                return f"{label}: {description}" if label else description
            
            # If no description, try to get label only
            query_label = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?label WHERE {{
                <{node_uri}> rdfs:label ?label .
            }}
            LIMIT 1
            """
            
            results, error = self.execute_sparql(query_label)
            if results:
                return str(results[0][0])
            
            return None
        except:
            return None
    
    def find_connections(self, resource1, resource2):
        """Find connections between two resources in both directions"""
        query = f"""
        SELECT DISTINCT ?connection_type ?path ?intermediate ?direction WHERE {{
            # Direct connection: resource1 -> resource2
            {{
                <{resource1}> ?path <{resource2}> .
                BIND("direct" AS ?connection_type)
                BIND("forward" AS ?direction)
                BIND("none" AS ?intermediate)
            }}
            UNION
            # Direct connection: resource2 -> resource1 (reverse)
            {{
                <{resource2}> ?path <{resource1}> .
                BIND("direct" AS ?connection_type)
                BIND("reverse" AS ?direction)
                BIND("none" AS ?intermediate)
            }}
            UNION
            # 2-hop connection: resource1 -> intermediate -> resource2
            {{
                <{resource1}> ?p1 ?intermediate .
                ?intermediate ?p2 <{resource2}> .
                FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>)
                BIND("2-hop" AS ?connection_type)
                BIND("forward" AS ?direction)
                BIND(CONCAT(STR(?p1), " -> ", STR(?p2)) AS ?path)
            }}
            UNION
            # 2-hop connection: resource2 -> intermediate -> resource1 (reverse)
            {{
                <{resource2}> ?p1 ?intermediate .
                ?intermediate ?p2 <{resource1}> .
                FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>)
                BIND("2-hop" AS ?connection_type)
                BIND("reverse" AS ?direction)
                BIND(CONCAT(STR(?p1), " -> ", STR(?p2)) AS ?path)
            }}
            UNION
            # Shared connection: both resources connected to same intermediate
            {{
                <{resource1}> ?p1 ?intermediate .
                <{resource2}> ?p2 ?intermediate .
                FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>)
                FILTER(?p1 = ?p2)  # Same property type
                BIND("shared" AS ?connection_type)
                BIND("bidirectional" AS ?direction)
                BIND(STR(?p1) AS ?path)
            }}
            UNION
            # Inverse shared connection: intermediate connected to both resources
            {{
                ?intermediate ?p1 <{resource1}> .
                ?intermediate ?p2 <{resource2}> .
                FILTER(?intermediate != <{resource1}> && ?intermediate != <{resource2}>)
                FILTER(?p1 = ?p2)  # Same property type
                BIND("inverse_shared" AS ?connection_type)
                BIND("bidirectional" AS ?direction)
                BIND(STR(?p1) AS ?path)
            }}
        }}
        ORDER BY ?connection_type ?direction
        """
        results, error = self.execute_sparql(query)
        return results, error

def main():
    # Header
    st.markdown('<div class="main-header"><h1>RDF Navigator</h1><p>Explore and navigate RDF semantic data with powerful SPARQL queries</p></div>', unsafe_allow_html=True)
    
    # Initialize RDF Navigator
    navigator = RDFNavigator()
    
    # Sidebar for file upload and navigation
    with st.sidebar:
        st.header("File Upload")
        uploaded_file = st.file_uploader(
            "Upload RDF Turtle (.ttl) file",
            type=['ttl'],
            help="Upload your RDF Turtle file containing semantic data"
        )
        
        if uploaded_file is not None:
            file_content = uploaded_file.read().decode('utf-8')
            success, message = navigator.load_ttl_file(file_content)
            
            if success:
                st.success(message)
                st.session_state.rdf_graph = navigator
                
                # Show graph statistics
                st.header("Graph Statistics")
                st.metric("Total Triples", len(navigator.graph))
                st.metric("Unique Resources", len(navigator.get_all_resources()))
                st.metric("Namespaces", len(navigator.namespaces))
                
                # Show namespaces
                if navigator.namespaces:
                    st.header("Namespaces")
                    for prefix, namespace in navigator.namespaces.items():
                        st.text(f"{prefix}: {namespace}")
            else:
                st.error(message)
        
        # Navigation history
        if st.session_state.navigation_history:
            st.header("Navigation History")
            for i, resource in enumerate(reversed(st.session_state.navigation_history[-5:])):
                if st.button(f"Back {navigator.shorten_uri(resource) if st.session_state.rdf_graph else resource}", key=f"nav_{i}"):
                    st.session_state.current_resource = resource
                    st.rerun()
    
    # Main content area
    if st.session_state.rdf_graph is None:
        st.info("Please upload an RDF Turtle (.ttl) file to begin exploration")
        return
    
    navigator = st.session_state.rdf_graph
    
    # Tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Graph Explorer", "SPARQL Queries", "Graph Visualization"])
    
    with tab1:
        st.header("Graph Explorer")
        
        # Resource input section
        col1, col2 = st.columns([3, 1])
        with col1:
            resource_input = st.text_input(
                "Enter Resource URI",
                value=st.session_state.current_resource or "",
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
                    st.session_state.current_resource = random_resource
                    st.rerun()
        
        # Button to explore the entered resource
        if resource_input:
            if st.button("Explore Resource", key="explore_button"):
                # Expand URI if it's prefixed
                expanded_uri = navigator.expand_uri(resource_input)
                st.session_state.current_resource = expanded_uri
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
            if selected_resource and selected_resource != st.session_state.current_resource:
                st.session_state.current_resource = selected_resource
                st.rerun()
        
        # Display current resource information
        current_resource = st.session_state.current_resource
        if current_resource:
            st.subheader(f"Resource Details: {navigator.shorten_uri(current_resource)}")
            st.code(current_resource, language="text")
            
            # Get triples for the resource
            triples = navigator.get_resource_triples(current_resource)
            
            if triples:
                # Add to navigation history
                if current_resource not in st.session_state.navigation_history:
                    st.session_state.navigation_history.append(current_resource)
                
                st.success(f"Found {len(triples)} triples for this resource")
                
                # Display triples in an organized way
                subjects = [t for t in triples if t[0] == 'subject']
                objects = [t for t in triples if t[0] == 'object']
                
                if subjects:
                    st.subheader("As Subject (outgoing relationships)")
                    for idx, (_, s, p, o) in enumerate(subjects):
                        with st.container():
                            st.markdown(f'<div class="triple-row">', unsafe_allow_html=True)
                            col1, col2, col3 = st.columns([2, 2, 2])
                            with col1:
                                st.write(f"**Property:** {navigator.shorten_uri(p)}")
                            with col2:
                                st.write(f"**Object:** {navigator.shorten_uri(o)}")
                            with col3:
                                # Check if object is a URI and not a literal
                                try:
                                    uri_ref = URIRef(o)
                                    if o.startswith('http') and not o.startswith('http://www.w3.org/2001/XMLSchema#'):
                                        if st.button(f"Navigate to {navigator.shorten_uri(o)}", key=f"nav_obj_{idx}_{hash(o)}"):
                                            st.session_state.current_resource = o
                                            st.rerun()
                                except:
                                    pass
                            st.markdown('</div>', unsafe_allow_html=True)
                
                if objects:
                    st.subheader("As Object (incoming relationships)")
                    for idx, (_, s, p, o) in enumerate(objects):
                        with st.container():
                            st.markdown(f'<div class="triple-row">', unsafe_allow_html=True)
                            col1, col2, col3 = st.columns([2, 2, 2])
                            with col1:
                                st.write(f"**Subject:** {navigator.shorten_uri(s)}")
                            with col2:
                                st.write(f"**Property:** {navigator.shorten_uri(p)}")
                            with col3:
                                # Check if subject is a URI and not a literal
                                try:
                                    uri_ref = URIRef(s)
                                    if s.startswith('http') and not s.startswith('http://www.w3.org/2001/XMLSchema#'):
                                        if st.button(f"Navigate to {navigator.shorten_uri(s)}", key=f"nav_subj_{idx}_{hash(s)}"):
                                            st.session_state.current_resource = s
                                            st.rerun()
                                except:
                                    pass
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("No triples found for this resource. Please check the URI or try a different resource.")
                
                # Show suggestion for available resources
                if resources:
                    st.info("Try one of these available resources:")
                    for i, res in enumerate(resources[:5]):
                        st.text(f"• {navigator.shorten_uri(res)}")
    
    with tab2:
        st.header("SPARQL Query Tools")
        
        # Query Scenario 1: Find Link Between Two IRs/Functions/ERs
        st.markdown('<div class="query-card">', unsafe_allow_html=True)
        st.subheader("Query 1: Find Links Between Two IRs/Functions/ERs")
        col1, col2 = st.columns(2)
        with col1:
            resource1 = st.text_input("First IR/ER ID", key="q1_r1", 
                                    help="Enter IR ID (e.g., 'IR_IR004') or ER ID (e.g., 'ER_ER004')")
        with col2:
            resource2 = st.text_input("Second IR/ER ID", key="q1_r2",
                                    help="Enter IR ID (e.g., 'IR_IR005') or ER ID (e.g., 'ER_ER005')")
        
        if st.button("Find Connections", key="q1_btn"):
            if resource1 and resource2:
                # Find IR/ER resources by ID
                expanded_r1 = navigator.find_ir_er_by_id(resource1)
                expanded_r2 = navigator.find_ir_er_by_id(resource2)
                
                if not expanded_r1:
                    st.error(f"IR/ER '{resource1}' not found. Try using ID like 'IR_IR004' or 'ER_ER004'.")
                    return
                if not expanded_r2:
                    st.error(f"IR/ER '{resource2}' not found. Try using ID like 'IR_IR005' or 'ER_ER005'.")
                    return
                
                results, error = navigator.find_connections(expanded_r1, expanded_r2)
                if error:
                    st.error(f"Query error: {error}")
                else:
                    if results:
                        st.success(f"Found {len(results)} connections between the resources")
                        
                        # Create a more detailed DataFrame
                        connection_data = []
                        for result in results:
                            connection_type = str(result[0])
                            path = str(result[1])
                            intermediate = str(result[2])
                            direction = str(result[3])
                            
                            # Format the connection description
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
                        
                        # Show additional info
                        st.info(f"Searched between:\n• **Resource 1**: {navigator.shorten_uri(expanded_r1)}\n• **Resource 2**: {navigator.shorten_uri(expanded_r2)}")
                    else:
                        st.info("No connections found between these resources")
                        st.warning("Try checking if the URIs are correct or if the resources exist in your RDF graph")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Query Scenario 2: Status of a Customer
        st.markdown('<div class="query-card">', unsafe_allow_html=True)
        st.subheader("Query 2: Customer Status")
        customer_name = st.text_input("Customer Name or URI", key="q2_customer",
                                    help="Enter customer name (e.g., 'Tesla') or URI (e.g., 'ex:Customer_Tesla')")
        
        if st.button("Get Customer Status", key="q2_btn"):
            if customer_name:
                # Try to find customer by name first, then expand URI
                expanded_customer = navigator.find_resource_by_name(customer_name)
                
                if not expanded_customer:
                    st.error(f"Customer '{customer_name}' not found. Try using full URI or check spelling.")
                    return
                
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
                else:
                    if results:
                        df = pd.DataFrame(results, columns=['Item', 'Type', 'Status', 'Title', 'Domain'])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No items found for this customer")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Query Scenario 3: Customers with Similar Requests - ENHANCED VERSION
        st.markdown('<div class="query-card">', unsafe_allow_html=True)
        st.subheader("Query 3: Customers with Similar Requests")
        domain_filter = st.text_input(
            "Domain to search for", 
            key="q3_domain",
            help="Enter a keyword (e.g., 'reporting') or full URI (e.g., 'http://example.org/dassault#Module_Reporting')"
        )
        
        if st.button("Find Similar Requests", key="q3_btn"):
            if domain_filter:
                # Expand URI if it's prefixed (e.g., ex:Module_Reporting)
                expanded_filter = navigator.expand_uri(domain_filter)
                
                # Enhanced query that handles both exact URI matches and keyword matching
                query = f"""
                PREFIX ex: <http://example.org/dassault#>
                
                SELECT DISTINCT ?customer ?item ?title ?domain WHERE {{
                    ?item ex:belongsToCustomer ?customer .
                    ?item ex:mentionsFunction ?domain .
                    OPTIONAL {{ ?item ex:description ?title }}
                    
                    # Combined filter: exact URI match OR keyword substring match
                    FILTER(
                        # Exact match for full URI (original or expanded)
                        ?domain = <{domain_filter}> ||
                        ?domain = <{expanded_filter}> ||
                        # Keyword match in the URI string (case-insensitive)
                        CONTAINS(LCASE(STR(?domain)), LCASE("{domain_filter}")) ||
                        # Keyword match with underscore-to-space conversion
                        CONTAINS(LCASE(REPLACE(STR(?domain), "_", " ")), LCASE("{domain_filter}")) ||
                        # Keyword match in local name (part after # or last /)
                        CONTAINS(LCASE(REPLACE(REPLACE(STR(?domain), "^.*[/#]", ""), "_", " ")), LCASE("{domain_filter}"))
                    )
                }}
                ORDER BY ?customer ?item
                """
                results, error = navigator.execute_sparql(query)
                if error:
                    st.error(f"Query error: {error}")
                else:
                    if results:
                        # Convert results to a more readable format
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
                        
                        # Show summary
                        unique_customers = df['Customer'].nunique()
                        st.info(f"Summary: {unique_customers} unique customers with requests related to '{domain_filter}'")
                        
                        # Show what was actually searched for
                        if expanded_filter != domain_filter:
                            st.info(f"Searched for: '{domain_filter}' (expanded to: {expanded_filter})")
                        else:
                            st.info(f"Searched for: '{domain_filter}'")
                    else:
                        st.info(f"No requests found for domain '{domain_filter}'")
                        st.warning("Try different domain names like 'security', 'reporting', 'authentication', etc.")
                        
                        # Show available domains for debugging
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
                    
                    # Filter for high priority incidents (P0, P1)
                    FILTER(?priority IN ("P0", "P1"))
                }
                ORDER BY ?priority ?severity
                """
                results, error = navigator.execute_sparql(query)
                if error:
                    st.error(f"Query error: {error}")
                else:
                    if results:
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
                        
                        # Summary statistics
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
                else:
                    if results:
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
                        
                        # Risk visualization
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
                else:
                    if results:
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
                        
                        # Pivot table for better visualization
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
                else:
                    if results:
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
                        
                        # Summary metrics
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
                else:
                    if results:
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
                        
                        # Pivot table for request types
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
                else:
                    if results:
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
                        
                        # Find modules with most issues per product
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
                else:
                    if results:
                        # Convert results to DataFrame
                        if results:
                            columns = [str(var) for var in results[0]]
                            data = [[str(binding) for binding in row] for row in results]
                            df = pd.DataFrame(data, columns=columns)
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Query returned no results")
    
    with tab3:
        st.header("Graph Visualization")
        
        if st.session_state.current_resource:
            st.subheader(f"Visualizing connections for: {navigator.shorten_uri(st.session_state.current_resource)}")
            
            # Create network visualization
            net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
            
            # Add current resource as central node
            current_uri = st.session_state.current_resource
            net.add_node(current_uri, label=navigator.shorten_uri(current_uri), color="#ff6b6b", size=25)
            
            # Get triples and add connected nodes
            triples = navigator.get_resource_triples(current_uri)
            added_nodes = {current_uri}
            node_descriptions = {}  # Store descriptions for nodes
            
            for triple_type, s, p, o in triples[:20]:  # Limit to first 20 for performance
                if triple_type == 'subject':
                    if o not in added_nodes:
                        # Get description for IR/ER nodes
                        description = navigator.get_node_description(o)
                        node_descriptions[o] = description
                        
                        # Color code based on node type
                        node_color = "#4ecdc4"  # Default
                        if "IR_" in str(o):
                            node_color = "#ff7675"  # Red for IRs
                        elif "ER_" in str(o):
                            node_color = "#74b9ff"  # Blue for ERs
                        elif "Module_" in str(o):
                            node_color = "#55a3ff"  # Light blue for modules
                        elif "Customer_" in str(o):
                            node_color = "#00b894"  # Green for customers
                        
                        net.add_node(o, label=navigator.shorten_uri(o), color=node_color, size=15)
                        added_nodes.add(o)
                    net.add_edge(s, o, label=navigator.shorten_uri(p), color="#95a5a6")
                else:
                    if s not in added_nodes:
                        # Get description for IR/ER nodes
                        description = navigator.get_node_description(s)
                        node_descriptions[s] = description
                        
                        # Color code based on node type
                        node_color = "#45b7d1"  # Default
                        if "IR_" in str(s):
                            node_color = "#ff7675"  # Red for IRs
                        elif "ER_" in str(s):
                            node_color = "#74b9ff"  # Blue for ERs
                        elif "Module_" in str(s):
                            node_color = "#55a3ff"  # Light blue for modules
                        elif "Customer_" in str(s):
                            node_color = "#00b894"  # Green for customers
                        
                        net.add_node(s, label=navigator.shorten_uri(s), color=node_color, size=15)
                        added_nodes.add(s)
                    net.add_edge(s, o, label=navigator.shorten_uri(p), color="#95a5a6")
            
            # Generate and display the network
            try:
                net.set_options("""
                var options = {
                    "physics": {
                        "enabled": true,
                        "stabilization": {"iterations": 100}
                    }
                }
                """)
                
                # Save to temporary file
                tmp_file = None
                try:
                    tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html')
                    net.save_graph(tmp_file.name)
                    tmp_file.close()
                    
                    # Read the HTML content
                    with open(tmp_file.name, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Display in Streamlit
                    st.components.v1.html(html_content, height=600)
                    
                    # Node descriptions section
                    if node_descriptions:
                        st.subheader("Node Descriptions")
                        st.info("Click on nodes in the graph above to see their details. Below are descriptions of connected nodes:")
                        
                        # Group descriptions by type
                        ir_descriptions = {k: v for k, v in node_descriptions.items() if v and "IR_" in str(k)}
                        er_descriptions = {k: v for k, v in node_descriptions.items() if v and "ER_" in str(k)}
                        module_descriptions = {k: v for k, v in node_descriptions.items() if v and "Module_" in str(k)}
                        customer_descriptions = {k: v for k, v in node_descriptions.items() if v and "Customer_" in str(k)}
                        
                        # Display IR descriptions
                        if ir_descriptions:
                            st.markdown("**Incident Reports (IRs):**")
                            for node, desc in ir_descriptions.items():
                                with st.expander(f"{navigator.shorten_uri(node)}"):
                                    st.write(desc)
                        
                        # Display ER descriptions
                        if er_descriptions:
                            st.markdown("**Enhancement Requests (ERs):**")
                            for node, desc in er_descriptions.items():
                                with st.expander(f"{navigator.shorten_uri(node)}"):
                                    st.write(desc)
                        
                        # Display Module descriptions
                        if module_descriptions:
                            st.markdown("**Modules:**")
                            for node, desc in module_descriptions.items():
                                with st.expander(f"{navigator.shorten_uri(node)}"):
                                    st.write(desc if desc else "Module information")
                        
                        # Display Customer descriptions
                        if customer_descriptions:
                            st.markdown("**Customers:**")
                            for node, desc in customer_descriptions.items():
                                with st.expander(f"{navigator.shorten_uri(node)}"):
                                    st.write(desc if desc else "Customer information")
                    
                except Exception as e:
                    st.error(f"Error generating visualization: {str(e)}")
                finally:
                    # Clean up - try to delete the file, but don't fail if it's locked
                    if tmp_file and os.path.exists(tmp_file.name):
                        try:
                            os.unlink(tmp_file.name)
                        except:
                            pass  # Ignore cleanup errors
                
            except Exception as e:
                st.error(f"Error generating visualization: {str(e)}")
        else:
            st.info("Navigate to a resource in the Graph Explorer to see its visualization")
        
        # Graph overview
        st.subheader("Graph Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Triples", len(navigator.graph))
        
        with col2:
            # Count distinct subjects
            subjects = set()
            for s, p, o in navigator.graph:
                subjects.add(s)
            st.metric("Distinct Subjects", len(subjects))
        
        with col3:
            # Count distinct predicates
            predicates = set()
            for s, p, o in navigator.graph:
                predicates.add(p)
            st.metric("Distinct Predicates", len(predicates))

if __name__ == "__main__":
    main()