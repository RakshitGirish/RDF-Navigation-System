# RDF Navigator

A Streamlit-based application for exploring and navigating RDF semantic data with powerful SPARQL queries. Built specifically for Dassault Systems-like data including Incident Reports (IRs), Enhancement Requests (ERs), Customers, and Modules.

## Features

- **Graph Explorer**: Navigate through RDF resources with interactive triple visualization
- **SPARQL Query Tools**: Pre-built queries for common scenarios:
  - Find links between IRs/Functions/ERs
  - Get customer status information
  - Find customers with similar requests
  - Priority Analysis & Risk Assessment
  - Product Performance Analysis
- **Graph Visualization**: Interactive network graphs with color-coded nodes
- **Custom SPARQL Queries**: Execute your own SPARQL queries
- **Rich Data Support**: Enhanced RDF data with detailed properties and relationships

## System Requirements

- Python 3.7 or higher
- Windows, macOS, or Linux
- At least 4GB RAM (recommended)
- Web browser for the Streamlit interface

## Installation Steps

### 1. Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd rdf-navigator

# Or download and extract the ZIP file
# Navigate to the extracted folder
```

### 2. Install Python Dependencies

The project uses several Python packages. Install them using pip:

```bash
# Install required packages
pip install streamlit
pip install pandas
pip install rdflib
pip install networkx
pip install pyvis
```

**Alternative: Create a Virtual Environment (Recommended)**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install streamlit pandas rdflib networkx pyvis
```

### 3. Verify Installation

Check if all dependencies are installed correctly:

```bash
python -c "import streamlit, pandas, rdflib, networkx, pyvis; print('All dependencies installed successfully!')"
```

## Project Structure

```
rdf-navigator/
├── rdf_navigator.py          # Main application file
├── dassault_rich.ttl         # Sample RDF data file
├── graph.html               # Graph visualization template
├── lib/                     # JavaScript/CSS libraries
│   ├── vis-9.1.2/          # Vis.js network visualization
│   │   ├── vis-network.css
│   │   └── vis-network.min.js
│   ├── tom-select/          # Enhanced select dropdowns
│   │   ├── tom-select.css
│   │   └── tom-select.complete.min.js
│   └── bindings/            # Custom JavaScript utilities
│       └── utils.js
└── venv/                    # Virtual environment (created during setup)
```

## Running the Application

### 1. Start the Streamlit App

```bash
# Make sure you're in the project directory
cd rdf-navigator

# Run the application
streamlit run rdf_navigator.py
```

### 2. Access the Application

- The app will automatically open in your default web browser
- If it doesn't open automatically, go to: `http://localhost:8501`
- The interface will show a file upload area in the sidebar

### 3. Load RDF Data

1. In the sidebar, click "Browse files" under "Upload RDF Turtle (.ttl) file"
2. Select the `dassault_rich.ttl` file (included with the project)
3. The app will load the data and show graph statistics

## Using the Application

### Graph Explorer Tab
- Enter resource URIs or use the dropdown to select resources
- Navigate through connected resources by clicking buttons
- View detailed triple information

### SPARQL Queries Tab
- **Query 1**: Find connections between two IRs/ERs (use IDs like "IR_IR004")
- **Query 2**: Get customer status (enter customer name like "Tesla")
- **Query 3**: Find similar requests (enter domain like "reporting")
- **Query 4**: Priority and risk analysis
- **Query 5**: Product performance analysis
- **Custom Query**: Write your own SPARQL queries

### Graph Visualization Tab
- Interactive network graphs with color-coded nodes
- Click on nodes to see detailed descriptions
- Explore connections visually

## Sample Data

The project includes `dassault_rich.ttl` with sample data containing:
- Incident Reports (IRs) with priorities, severities, and statuses
- Enhancement Requests (ERs) with request types and priorities
- Customer information with domains and contact details
- Module information with versions and descriptions
- Rich relationships and cross-references

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Use a different port
   streamlit run rdf_navigator.py --server.port 8502
   ```

2. **Missing dependencies**
   ```bash
   # Reinstall dependencies
   pip install --upgrade streamlit pandas rdflib networkx pyvis
   ```

3. **File permission errors (Windows)**
   - Run PowerShell as Administrator
   - Or use a different directory for the project

4. **Browser compatibility**
   - Use Chrome, Firefox, or Edge
   - Ensure JavaScript is enabled

### Performance Tips

- For large RDF files (>10MB), the app may take longer to load
- The graph visualization is limited to 20 connections for performance
- Use specific URIs rather than broad searches for better performance

## Customization

### Adding Your Own RDF Data

1. Create a Turtle (.ttl) file with your RDF data
2. Follow the same namespace structure as the sample data
3. Upload your file through the interface

### Modifying Queries

Edit the SPARQL queries in `rdf_navigator.py` to match your data structure:
- Update namespace prefixes
- Modify property names
- Adjust query patterns

### Styling

The app uses custom CSS for styling. Modify the CSS section in `rdf_navigator.py` to change the appearance.

## Support

If you encounter issues:
1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure your RDF file is valid Turtle format
4. Check that the file encoding is UTF-8

## License

This project is provided as-is for educational and development purposes. 