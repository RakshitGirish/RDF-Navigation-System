#!/usr/bin/env python3
"""
CSV to RDF TTL Converter for Dassault Data
Converts CSV files containing Dassault data to RDF Turtle format
"""

import pandas as pd
import argparse
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

class CSVToRDFConverter:
    def __init__(self):
        self.namespace = "http://example.org/dassault#"
        self.prefix = "ex"
        
    def clean_text(self, text: str) -> str:
        """Clean and escape text for RDF"""
        if pd.isna(text) or text is None:
            return ""
        text = str(text).strip()
        # Escape quotes and backslashes
        text = text.replace('\\', '\\\\').replace('"', '\\"')
        return text
    
    def format_date(self, date_str: str) -> str:
        """Format date string to DD-MM-YYYY format"""
        if pd.isna(date_str) or not date_str:
            return ""
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    date_obj = datetime.strptime(str(date_str), fmt)
                    return date_obj.strftime('%d-%m-%Y')
                except ValueError:
                    continue
            return str(date_str)
        except:
            return str(date_str)
    
    def create_uri(self, entity_type: str, identifier: str) -> str:
        """Create URI for entity"""
        clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', str(identifier))
        return f"{self.prefix}:{entity_type}_{clean_id}"
    
    def write_prefixes(self, output_file) -> None:
        """Write RDF prefixes"""
        output_file.write(f"@prefix {self.prefix}: <{self.namespace}> .\n")
        output_file.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        output_file.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n")
    
    def process_enhancement_requests(self, df: pd.DataFrame, output_file) -> None:
        """Process Enhancement Requests from CSV"""
        if 'ER' not in df.columns and 'enhancement' not in df.columns:
            return
            
        er_column = 'ER' if 'ER' in df.columns else 'enhancement'
        
        for _, row in df.iterrows():
            if pd.isna(row[er_column]) or not row[er_column]:
                continue
                
            er_id = str(row[er_column]).strip()
            er_uri = self.create_uri("ER", er_id)
            
            output_file.write(f"{er_uri} a {self.prefix}:EnhancementRequest ;\n")
            
            # Required fields
            if 'customer' in df.columns and not pd.isna(row['customer']):
                customer_uri = self.create_uri("Customer", row['customer'])
                output_file.write(f"    {self.prefix}:belongsToCustomer {customer_uri} ;\n")
            
            if 'created_on' in df.columns and not pd.isna(row['created_on']):
                date_str = self.format_date(row['created_on'])
                if date_str:
                    output_file.write(f'    {self.prefix}:createdOn "{date_str}"^^xsd:date ;\n')
            
            if 'description' in df.columns and not pd.isna(row['description']):
                desc = self.clean_text(row['description'])
                if desc:
                    output_file.write(f'    {self.prefix}:description "{desc}" ;\n')
            
            # Optional fields
            if 'priority' in df.columns and not pd.isna(row['priority']):
                priority = self.clean_text(row['priority'])
                if priority:
                    output_file.write(f'    {self.prefix}:priority "{priority}" ;\n')
            
            if 'product' in df.columns and not pd.isna(row['product']):
                product = self.clean_text(row['product'])
                if product:
                    output_file.write(f'    {self.prefix}:product "{product}" ;\n')
            
            if 'request_type' in df.columns and not pd.isna(row['request_type']):
                req_type = self.clean_text(row['request_type'])
                if req_type:
                    output_file.write(f'    {self.prefix}:requestType "{req_type}" ;\n')
            
            if 'status' in df.columns and not pd.isna(row['status']):
                status = self.clean_text(row['status'])
                if status:
                    output_file.write(f'    {self.prefix}:status "{status}" ;\n')
            
            if 'module' in df.columns and not pd.isna(row['module']):
                module_uri = self.create_uri("Module", row['module'])
                output_file.write(f"    {self.prefix}:mentionsFunction {module_uri} ;\n")
            
            # Similar items (if provided)
            if 'similar_to' in df.columns and not pd.isna(row['similar_to']):
                similar_items = str(row['similar_to']).split(',')
                similar_uris = []
                for item in similar_items:
                    item = item.strip()
                    if item:
                        if item.startswith('ER_'):
                            similar_uris.append(self.create_uri("ER", item))
                        elif item.startswith('IR_'):
                            similar_uris.append(self.create_uri("IR", item))
                
                if similar_uris:
                    output_file.write(f"    {self.prefix}:isSimilarTo {', '.join(similar_uris)} ;\n")
            
            # Remove last semicolon and add period
            output_file.seek(output_file.tell() - 2)
            output_file.write(" .\n\n")
    
    def process_incident_reports(self, df: pd.DataFrame, output_file) -> None:
        """Process Incident Reports from CSV"""
        if 'IR' not in df.columns and 'incident' not in df.columns:
            return
            
        ir_column = 'IR' if 'IR' in df.columns else 'incident'
        
        for _, row in df.iterrows():
            if pd.isna(row[ir_column]) or not row[ir_column]:
                continue
                
            ir_id = str(row[ir_column]).strip()
            ir_uri = self.create_uri("IR", ir_id)
            
            output_file.write(f"{ir_uri} a {self.prefix}:IncidentReport ;\n")
            
            # Label (title)
            if 'title' in df.columns and not pd.isna(row['title']):
                title = self.clean_text(row['title'])
                if title:
                    output_file.write(f'    rdfs:label "{title}" ;\n')
            
            # Required fields
            if 'customer' in df.columns and not pd.isna(row['customer']):
                customer_uri = self.create_uri("Customer", row['customer'])
                output_file.write(f"    {self.prefix}:belongsToCustomer {customer_uri} ;\n")
            
            if 'created_on' in df.columns and not pd.isna(row['created_on']):
                date_str = self.format_date(row['created_on'])
                if date_str:
                    output_file.write(f'    {self.prefix}:createdOn "{date_str}"^^xsd:date ;\n')
            
            if 'description' in df.columns and not pd.isna(row['description']):
                desc = self.clean_text(row['description'])
                if desc:
                    output_file.write(f'    {self.prefix}:description "{desc}" ;\n')
            
            # Optional fields
            if 'priority' in df.columns and not pd.isna(row['priority']):
                priority = self.clean_text(row['priority'])
                if priority:
                    output_file.write(f'    {self.prefix}:priority "{priority}" ;\n')
            
            if 'severity' in df.columns and not pd.isna(row['severity']):
                severity = self.clean_text(row['severity'])
                if severity:
                    output_file.write(f'    {self.prefix}:severity "{severity}" ;\n')
            
            if 'product' in df.columns and not pd.isna(row['product']):
                product = self.clean_text(row['product'])
                if product:
                    output_file.write(f'    {self.prefix}:product "{product}" ;\n')
            
            if 'status' in df.columns and not pd.isna(row['status']):
                status = self.clean_text(row['status'])
                if status:
                    output_file.write(f'    {self.prefix}:status "{status}" ;\n')
            
            if 'module' in df.columns and not pd.isna(row['module']):
                module_uri = self.create_uri("Module", row['module'])
                output_file.write(f"    {self.prefix}:mentionsFunction {module_uri} ;\n")
            
            # Similar items (if provided)
            if 'similar_to' in df.columns and not pd.isna(row['similar_to']):
                similar_items = str(row['similar_to']).split(',')
                similar_uris = []
                for item in similar_items:
                    item = item.strip()
                    if item:
                        if item.startswith('ER_'):
                            similar_uris.append(self.create_uri("ER", item))
                        elif item.startswith('IR_'):
                            similar_uris.append(self.create_uri("IR", item))
                
                if similar_uris:
                    output_file.write(f"    {self.prefix}:isSimilarTo {', '.join(similar_uris)} ;\n")
            
            # Remove last semicolon and add period
            output_file.seek(output_file.tell() - 2)
            output_file.write(" .\n\n")
    
    def process_modules(self, df: pd.DataFrame, output_file) -> None:
        """Process Modules from CSV"""
        if 'module' not in df.columns and 'Module' not in df.columns:
            return
            
        module_column = 'Module' if 'Module' in df.columns else 'module'
        unique_modules = set()
        
        # Collect unique modules from all data
        for _, row in df.iterrows():
            if not pd.isna(row[module_column]) and row[module_column]:
                unique_modules.add(str(row[module_column]).strip())
        
        for module_name in unique_modules:
            if not module_name:
                continue
                
            module_uri = self.create_uri("Module", module_name)
            output_file.write(f"{module_uri} a {self.prefix}:Module ;\n")
            output_file.write(f'    rdfs:label "{self.clean_text(module_name)}" .\n\n')
    
    def process_customers(self, df: pd.DataFrame, output_file) -> None:
        """Process Customers from CSV"""
        if 'customer' not in df.columns and 'Customer' not in df.columns:
            return
            
        customer_column = 'Customer' if 'Customer' in df.columns else 'customer'
        unique_customers = set()
        
        # Collect unique customers from all data
        for _, row in df.iterrows():
            if not pd.isna(row[customer_column]) and row[customer_column]:
                unique_customers.add(str(row[customer_column]).strip())
        
        for customer_name in unique_customers:
            if not customer_name:
                continue
                
            customer_uri = self.create_uri("Customer", customer_name)
            output_file.write(f"{customer_uri} a {self.prefix}:Customer ;\n")
            output_file.write(f'    rdfs:label "{self.clean_text(customer_name)}"')
            
            # Add domain if available
            if 'domain' in df.columns:
                # Find domain for this customer
                customer_rows = df[df[customer_column] == customer_name]
                if not customer_rows.empty and not pd.isna(customer_rows.iloc[0]['domain']):
                    domain = self.clean_text(customer_rows.iloc[0]['domain'])
                    if domain:
                        output_file.write(f' ;\n    {self.prefix}:domain "{domain}"')
            
            output_file.write(" .\n\n")
    
    def convert_csv_to_ttl(self, csv_files: List[str], output_file: str) -> None:
        """Convert CSV files to TTL format"""
        print(f"Converting {len(csv_files)} CSV file(s) to TTL format...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write prefixes
            self.write_prefixes(f)
            
            # Process each CSV file
            for csv_file in csv_files:
                print(f"Processing {csv_file}...")
                
                try:
                    # Try different CSV reading options
                    df = None
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            df = pd.read_csv(csv_file, encoding=encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if df is None:
                        print(f"Warning: Could not read {csv_file} with any encoding")
                        continue
                    
                    # Clean column names
                    df.columns = [col.strip().lower() for col in df.columns]
                    
                    # Process different entity types
                    self.process_enhancement_requests(df, f)
                    self.process_incident_reports(df, f)
                    self.process_modules(df, f)
                    self.process_customers(df, f)
                    
                except Exception as e:
                    print(f"Error processing {csv_file}: {str(e)}")
                    continue
        
        print(f"Conversion completed! Output saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Convert CSV files to RDF TTL format')
    parser.add_argument('csv_files', nargs='+', help='Input CSV file(s)')
    parser.add_argument('-o', '--output', default='output.ttl', help='Output TTL file (default: output.ttl)')
    parser.add_argument('--namespace', default='http://example.org/dassault#', help='RDF namespace (default: http://example.org/dassault#)')
    parser.add_argument('--prefix', default='ex', help='RDF prefix (default: ex)')
    
    args = parser.parse_args()
    
    # Validate input files
    for csv_file in args.csv_files:
        if not os.path.exists(csv_file):
            print(f"Error: File {csv_file} does not exist")
            sys.exit(1)
    
    # Create converter and convert
    converter = CSVToRDFConverter()
    converter.namespace = args.namespace
    converter.prefix = args.prefix
    
    try:
        converter.convert_csv_to_ttl(args.csv_files, args.output)
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 