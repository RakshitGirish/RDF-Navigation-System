# Quick Start Guide

## For Windows Users

### Option 1: Automated Setup (Recommended)
1. Double-click `setup.bat`
2. Follow the prompts
3. When setup completes, run: `venv\Scripts\activate`
4. Then run: `streamlit run rdf_navigator.py`

### Option 2: Manual Setup
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run rdf_navigator.py
```

## For macOS/Linux Users

### Option 1: Automated Setup (Recommended)
1. Open terminal in project directory
2. Run: `./setup.sh`
3. When setup completes, run: `source venv/bin/activate`
4. Then run: `streamlit run rdf_navigator.py`

### Option 2: Manual Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run rdf_navigator.py
```

## What You Need

- **Python 3.7+** (download from python.org if not installed)
- **Web browser** (Chrome, Firefox, Edge)
- **All project files** (make sure you have the complete folder)

## First Run

1. The app will open in your browser at `http://localhost:8501`
2. In the sidebar, click "Browse files" under "Upload RDF Turtle (.ttl) file"
3. Select `dassault_rich.ttl` (included with the project)
4. Start exploring the data!

## Troubleshooting

- **"Python not found"**: Install Python from python.org
- **"Port already in use"**: Use `streamlit run rdf_navigator.py --server.port 8502`
- **"Permission denied"**: Run as administrator (Windows) or use `sudo` (macOS/Linux)
- **Browser issues**: Try a different browser or clear cache

## Need Help?

Check the full `README.md` for detailed instructions and troubleshooting. 