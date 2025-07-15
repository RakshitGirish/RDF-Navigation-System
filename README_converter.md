# CSV to RDF TTL Converter for Dassault Data

This Python script converts CSV files containing Dassault Systems data into RDF Turtle (.ttl) format, matching the exact structure of the provided ERIR.ttl file.

## Features

- **Multiple CSV Support**: Process one or more CSV files at once
- **Flexible Column Mapping**: Automatically detects and maps CSV columns to RDF properties
- **Date Format Handling**: Supports multiple date formats and converts to DD-MM-YYYY
- **Text Escaping**: Properly escapes special characters for RDF compatibility
- **Entity Generation**: Creates EnhancementRequests, IncidentReports, Modules, and Customers
- **Similarity Links**: Handles `isSimilarTo` relationships between entities

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements_converter.txt
   ```

2. **Or install manually**:
   ```bash
   pip install pandas
   ```

## Usage

### Basic Usage

```bash
python csv_to_rdf_converter.py input.csv -o output.ttl
```

### Multiple CSV Files

```bash
python csv_to_rdf_converter.py file1.csv file2.csv file3.csv -o combined_output.ttl
```

### Custom Namespace and Prefix

```bash
python csv_to_rdf_converter.py input.csv -o output.ttl --namespace "http://mycompany.com/dassault#" --prefix "my"
```

### Command Line Options

- `csv_files`: One or more input CSV files (required)
- `-o, --output`: Output TTL file (default: output.ttl)
- `--namespace`: RDF namespace (default: http://example.org/dassault#)
- `--prefix`: RDF prefix (default: ex)

## CSV Format Requirements

### Enhancement Requests (ERs)

Your CSV should have a column named `ER` or `enhancement` containing ER IDs. Supported columns:

| Column | Description | Required | Example |
|--------|-------------|----------|---------|
| `ER` or `enhancement` | ER identifier | Yes | `ER_ER004` |
| `customer` | Customer name | Yes | `Tesla` |
| `created_on` | Creation date | Yes | `22-01-2024` |
| `description` | ER description | Yes | `Implement real-time collaboration features` |
| `priority` | Priority level | No | `P1` |
| `product` | Product name | No | `3DEXPERIENCE` |
| `request_type` | Type of request | No | `Feature` |
| `status` | Current status | No | `Go` |
| `module` | Related module | No | `Collaboration` |
| `similar_to` | Comma-separated similar items | No | `ER_ER025,ER_ER041,IR_IR004` |

### Incident Reports (IRs)

Your CSV should have a column named `IR` or `incident` containing IR IDs. Supported columns:

| Column | Description | Required | Example |
|--------|-------------|----------|---------|
| `IR` or `incident` | IR identifier | Yes | `IR_IR004` |
| `title` | IR title | Yes | `Collaboration server becomes unresponsive` |
| `customer` | Customer name | Yes | `Tesla` |
| `created_on` | Creation date | Yes | `18-01-2024` |
| `description` | IR description | Yes | `Real-time collaboration features freeze during peak usage` |
| `priority` | Priority level | No | `P0` |
| `severity` | Severity level | No | `Critical` |
| `product` | Product name | No | `3DEXPERIENCE` |
| `status` | Current status | No | `Open` |
| `module` | Related module | No | `Collaboration` |
| `similar_to` | Comma-separated similar items | No | `ER_ER004,ER_ER025,IR_IR025` |

### Column Name Flexibility

The converter automatically normalizes column names:
- Converts to lowercase
- Removes extra whitespace
- Handles variations like `Customer`, `customer`, `CUSTOMER`

## Sample CSV Files

### Sample Data Structure

```csv
ER,customer,created_on,description,priority,product,request_type,status,module,similar_to
ER_ER004,Tesla,22-01-2024,Implement real-time collaboration features,P1,3DEXPERIENCE,Feature,Go,Collaboration,ER_ER025,ER_ER041,ER_ER057,ER_ER073,ER_ER089,IR_IR004,IR_IR025,IR_IR041,IR_IR057,IR_IR073,IR_IR089
ER_ER005,Rolls-Royce,25-01-2024,Optimize memory usage for complex simulations,P1,SIMULIA,Performance,Go,Solver,ER_ER024,ER_ER040,ER_ER056,ER_ER072,ER_ER088,IR_IR005,IR_IR024,IR_IR040,IR_IR056,IR_IR072,IR_IR088
IR,title,customer,created_on,description,priority,severity,product,status,module,similar_to
IR_IR004,Collaboration server becomes unresponsive,Tesla,18-01-2024,Real-time collaboration features freeze during peak usage,P0,Critical,3DEXPERIENCE,Open,Collaboration,ER_ER004,ER_ER025,ER_ER041,ER_ER057,ER_ER073,ER_ER089,IR_IR025,IR_IR041,IR_IR057,IR_IR073,IR_IR089
```

## Output Format

The converter generates RDF Turtle format matching your ERIR.ttl structure:

```turtle
@prefix ex: <http://example.org/dassault#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:ER_ER004 a ex:EnhancementRequest ;
    ex:belongsToCustomer ex:Customer_Tesla ;
    ex:createdOn "22-01-2024"^^xsd:date ;
    ex:description "Implement real-time collaboration features" ;
    ex:isSimilarTo ex:ER_ER025,
        ex:ER_ER041,
        ex:ER_ER057,
        ex:ER_ER073,
        ex:ER_ER089,
        ex:IR_IR004,
        ex:IR_IR025,
        ex:IR_IR041,
        ex:IR_IR057,
        ex:IR_IR073,
        ex:IR_IR089 ;
    ex:mentionsFunction ex:Module_Collaboration ;
    ex:priority "P1" ;
    ex:product "3DEXPERIENCE" ;
    ex:requestType "Feature" ;
    ex:status "Go" .

ex:IR_IR004 a ex:IncidentReport ;
    rdfs:label "Collaboration server becomes unresponsive" ;
    ex:belongsToCustomer ex:Customer_Tesla ;
    ex:createdOn "18-01-2024"^^xsd:date ;
    ex:description "Real-time collaboration features freeze during peak usage" ;
    ex:isSimilarTo ex:ER_ER004,
        ex:ER_ER025,
        ex:ER_ER041,
        ex:ER_ER057,
        ex:ER_ER073,
        ex:ER_ER089,
        ex:IR_IR025,
        ex:IR_IR041,
        ex:IR_IR057,
        ex:IR_IR073,
        ex:IR_IR089 ;
    ex:mentionsFunction ex:Module_Collaboration ;
    ex:priority "P0" ;
    ex:product "3DEXPERIENCE" ;
    ex:severity "Critical" ;
    ex:status "Open" .

ex:Module_Collaboration a ex:Module ;
    rdfs:label "Collaboration" .

ex:Customer_Tesla a ex:Customer ;
    rdfs:label "Tesla" .
```

## Date Format Support

The converter supports multiple date formats:
- `YYYY-MM-DD` (2024-01-22)
- `DD/MM/YYYY` (22/01/2024)
- `MM/DD/YYYY` (01/22/2024)
- `DD-MM-YYYY` (22-01-2024)
- `YYYY/MM/DD` (2024/01/22)

All dates are converted to `DD-MM-YYYY` format in the output.

## Error Handling

- **Missing Files**: Script exits with error if input files don't exist
- **Encoding Issues**: Tries multiple encodings (UTF-8, Latin-1, CP1252)
- **Invalid Data**: Skips rows with missing required fields
- **Special Characters**: Properly escapes quotes and backslashes

## Examples

### Example 1: Single CSV File
```bash
python csv_to_rdf_converter.py my_data.csv -o my_output.ttl
```

### Example 2: Multiple CSV Files
```bash
python csv_to_rdf_converter.py er_data.csv ir_data.csv -o combined.ttl
```

### Example 3: Custom Namespace
```bash
python csv_to_rdf_converter.py data.csv -o output.ttl --namespace "http://mycompany.com/dassault#" --prefix "my"
```

## Troubleshooting

### Common Issues

1. **"File does not exist"**
   - Check file path and spelling
   - Use absolute paths if needed

2. **"Could not read file with any encoding"**
   - Check if file is corrupted
   - Try opening in a text editor to verify format

3. **Missing entities in output**
   - Check required columns are present
   - Verify data is not empty or malformed

4. **Date format issues**
   - Ensure dates are in supported formats
   - Check for extra spaces or special characters

### Debugging Tips

- Run with a small sample file first
- Check CSV column names match expected format
- Verify data types (dates, text, etc.)
- Use `--output` to specify output file location

## Integration with RDF Navigator

The generated TTL file can be directly used with the RDF Navigator application:

1. Convert your CSV data to TTL format
2. Upload the TTL file to RDF Navigator
3. Explore the semantic relationships and run SPARQL queries

## License

This converter is provided as-is for converting Dassault Systems data to RDF format. 