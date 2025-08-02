# RDF Navigator Unified Application

A comprehensive web-based application for exploring, querying, and visualizing RDF (Resource Description Framework) semantic data. Built with Streamlit, this application provides powerful tools for navigating linked data, executing SPARQL queries, and converting CSV data to RDF format.

## 🚀 Features

### 📊 **Graph Explorer**
- **Interactive Resource Navigation**: Explore RDF resources by URI or namespace prefix
- **Triple Visualization**: View incoming and outgoing relationships for any resource
- **Clickable Navigation**: Navigate between connected resources with one click
- **Resource Search**: Find resources by name, ID, or partial URI
- **Navigation History**: Track your exploration path through the knowledge graph

### 🔍 **SPARQL Queries**
- **Custom SPARQL Editor**: Write and execute custom SPARQL queries
- **Pre-built Query Templates**: Common analysis queries for:
  - Customer incident analysis
  - Module risk assessment
  - Priority and severity analysis
  - Cross-domain relationships
- **Query Results Visualization**: Interactive tables and charts
- **Query History**: Save and reuse successful queries

### 🎨 **Graph Visualization**
- **Interactive Network Graphs**: Visualize resource connections using pyvis
- **Color-coded Nodes**: Different colors for different entity types (IRs, ERs, Modules, Customers)
- **Clickable Nodes**: Click on graph nodes to navigate to resources
- **Relationship Labels**: See property names on graph edges
- **Node Descriptions**: Expandable details for each connected resource

### 📁 **File Management**
- **CSV to RDF Conversion**: Upload CSV files and convert them to RDF triples
- **File Tracking**: Monitor uploaded files with metadata
- **Triple Store Integration**: Store converted data in a SPARQL endpoint
- **File Operations**: Delete files and their associated triples
- **Export Capabilities**: Download converted TTL files

## 🛠️ Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **RDF Processing**: rdflib (Python RDF library)
- **Graph Visualization**: pyvis (Interactive network graphs)
- **Data Processing**: pandas (CSV handling and data manipulation)
- **Triple Store**: SPARQL endpoint integration
- **File Management**: JSON-based metadata storage

## 📋 Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- Web browser
- Optional: SPARQL endpoint for persistent data storage

## 🚀 Installation & Setup

### 1. Clone or Download the Application
```bash
# If using git
git clone <repository-url>
cd rdf-navigator

# Or download and extract the files
```

### 2. Install Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required packages
pip install streamlit pandas rdflib requests pyvis
```

### 3. Run the Application
```bash
streamlit run rdf_navigator_unified.py
```

The application will open in your default web browser at `http://localhost:8501`

## 📖 Usage Guide

### Getting Started

1. **Upload Data**: Start by uploading CSV files or RDF Turtle (.ttl) files
2. **Choose Data Source**: Select between local file or SPARQL endpoint
3. **Explore**: Use the Graph Explorer tab to navigate your data
4. **Query**: Execute SPARQL queries in the dedicated tab
5. **Visualize**: See interactive graphs in the Graph Visualization tab
6. **Manage**: Handle files in the File Management tab

### Graph Explorer

#### Finding Resources
- **Direct URI Input**: Enter a full URI (e.g., `http://example.org/dassault#IR001`)
- **Namespace Prefix**: Use shortened form (e.g., `ex:IR001`)
- **Random Resource**: Click "Random Resource" to explore random data
- **Resource Dropdown**: Select from available resources

#### Navigating Relationships
- **As Subject**: See outgoing relationships (what this resource points to)
- **As Object**: See incoming relationships (what points to this resource)
- **Click Navigation**: Click "Navigate to" buttons to explore connected resources

### SPARQL Queries

#### Custom Queries
1. Write your SPARQL query in the text area
2. Click "Execute Query" to run it
3. View results in the interactive table
4. Use "Save Query" to store for later use

#### Pre-built Analysis Queries
- **Customer Analysis**: Find incidents by customer with details
- **Module Analysis**: Analyze module-related incidents and requests
- **Priority Analysis**: High-priority incidents and risk assessment
- **Cross-Domain Analysis**: Relationships between different domains

### Graph Visualization

#### Interactive Features
- **Zoom**: Scroll to zoom in/out
- **Pan**: Click and drag to move around
- **Node Click**: Click on nodes to navigate to that resource
- **Hover**: Hover over nodes and edges for details

#### Node Types
- **Incident Reports (IRs)**: Red nodes
- **Enhancement Requests (ERs)**: Blue nodes  
- **Modules**: Light blue nodes
- **Customers**: Green nodes

### File Management

#### Uploading Files
1. Go to Graph Explorer tab
2. Use the sidebar file uploader
3. Select one or more CSV files
4. Files are automatically converted to RDF and stored

#### Managing Files
- **View Metadata**: File size, upload time, triple count
- **Preview TTL**: See the generated RDF data
- **Delete Files**: Remove files and their associated triples
- **Download TTL**: Export converted RDF data
- **Bulk Operations**: Delete all files or export file list

## 🔧 Configuration

### Data Sources

#### Local File Mode
- Upload RDF Turtle (.ttl) files directly
- Data is loaded into memory for the session
- Good for small datasets and testing

#### SPARQL Endpoint Mode
- Connect to a SPARQL endpoint for persistent storage
- Supports larger datasets and multi-user access
- Configure endpoint URL in the application

### Namespace Configuration
The application uses the default namespace:
- **Namespace**: `http://example.org/dassault#`
- **Prefix**: `ex`

You can modify this in the `CSVToRDFConverter` class if needed.

## 📊 Data Model

The application is designed to work with Dassault Systems data, including:

### Entity Types
- **Incident Reports (IR)**: Customer-reported issues
- **Enhancement Requests (ER)**: Feature requests
- **Modules**: Software modules/components
- **Customers**: Client organizations

### Key Properties
- `belongsToCustomer`: Links incidents/requests to customers
- `mentionsFunction`: Links to affected modules
- `severity`: Issue severity level
- `priority`: Issue priority level
- `status`: Current status (Open, Closed, etc.)
- `sourceFile`: Tracks which file created each triple

## 🎯 Use Cases

### Business Intelligence
- Analyze customer incident patterns
- Identify high-risk modules
- Track enhancement request trends
- Monitor issue resolution times

### Data Exploration
- Navigate complex RDF datasets
- Discover hidden relationships
- Explore semantic connections
- Visualize knowledge graphs

### Data Integration
- Convert CSV data to RDF format
- Integrate multiple data sources
- Create linked data from structured data
- Build semantic data warehouses

## 🔍 Troubleshooting

### Common Issues

#### Application Won't Start
- Check Python version (3.7+ required)
- Verify all dependencies are installed
- Ensure virtual environment is activated

#### No Data Visible
- Upload CSV files or RDF data first
- Check file format compatibility
- Verify SPARQL endpoint connectivity

#### Graph Visualization Issues
- Ensure JavaScript is enabled in browser
- Check for large datasets (may cause performance issues)
- Try refreshing the page

#### File Upload Errors
- Check file format (CSV or TTL)
- Verify file size (large files may timeout)
- Ensure proper file encoding (UTF-8 recommended)

### Performance Tips
- Use SPARQL endpoint for large datasets
- Limit graph visualization to focused queries
- Use filters in SPARQL queries to reduce result sets
- Consider data preprocessing for very large files

## 🤝 Contributing

This application is designed to be extensible. Key areas for enhancement:

- **Additional Data Formats**: Support for more input formats
- **Advanced Visualizations**: More graph visualization options
- **Query Templates**: Industry-specific query templates
- **Export Options**: Additional export formats
- **Performance Optimization**: Better handling of large datasets

## 📄 License

This application is provided as-is for educational and research purposes.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the application logs for error messages
3. Ensure all dependencies are properly installed
4. Verify data format compatibility

---

**RDF Navigator Unified Application** - Explore, query, and visualize semantic data with ease! 
