# Setup Checklist

## Before You Start
- [ ] Python 3.7 or higher installed
- [ ] All project files downloaded/extracted
- [ ] Web browser ready (Chrome, Firefox, Edge)

## Installation Steps
- [ ] Run setup script (`setup.bat` on Windows, `./setup.sh` on macOS/Linux)
- [ ] Or manually create virtual environment and install dependencies
- [ ] Virtual environment created successfully
- [ ] All dependencies installed without errors

## Verification Steps
- [ ] Run: `python -c "import streamlit, pandas, rdflib, networkx, pyvis; print('All dependencies installed successfully!')"`
- [ ] No error messages in the verification command
- [ ] Virtual environment can be activated

## Running the Application
- [ ] Activate virtual environment
- [ ] Run: `streamlit run rdf_navigator.py`
- [ ] Browser opens automatically or navigate to `http://localhost:8501`
- [ ] Streamlit interface loads without errors

## Loading Data
- [ ] Upload `dassault_rich.ttl` file in the sidebar
- [ ] Success message appears
- [ ] Graph statistics are displayed
- [ ] No error messages during data loading

## Testing Functionality
- [ ] Graph Explorer tab works
- [ ] SPARQL Queries tab works
- [ ] Graph Visualization tab works
- [ ] Can navigate between resources
- [ ] Queries return results

## If Any Step Fails
1. Check the error message
2. Refer to troubleshooting section in README.md
3. Verify Python version and dependencies
4. Try running as administrator (Windows) or with sudo (macOS/Linux)
5. Check if port 8501 is available

## Success!
If all checkboxes are marked, your RDF Navigator is ready to use! 