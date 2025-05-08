import os
import pandas as pd
import json
from collections import defaultdict
import re
from pathlib import Path
from datetime import datetime

def create_crop_inventory(root_directory):
    """
    Traverse the M49 directory structure and create a comprehensive inventory
    of crop data from LA_cropdata.csv files.
    """
    # Structure to hold our inventory data
    inventory = defaultdict(lambda: defaultdict(lambda: {
        'years': set(),
        'seasonality': set(),
        'area_planted': False,
        'area_harvested': False,
        'quantity_produced': False,
        'production': False,
        'regions': set(),  
        'data_sources': set(),  
        'indicators': set()  
    }))
    
    # Track statistics for reporting
    file_count = 0
    row_count = 0
    error_count = 0
    country_set = set()
    crop_set = set()
    
    # Walk through all directories
    for dirpath, dirnames, filenames in os.walk(root_directory):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        
        # Process CSV files
        for filename in filenames:
            if filename.lower() == 'la_cropdata.csv' or 'cropdata' in filename.lower():
                try:
                    file_path = os.path.join(dirpath, filename)
                    print(f"Processing {file_path}")
                    
                    # Read the CSV file
                    df = pd.read_csv(file_path)
                    row_count += len(df)
                    
                    # Process each row
                    for _, row in df.iterrows():
                        try:
                            country_code = row.get('country_code')
                            # Skip if no country code
                            if pd.isna(country_code):
                                continue
                            
                            country_set.add(country_code)
                                
                            # Get crop information (from product or cpcv2_description)
                            crop = row.get('product', '')
                            if pd.isna(crop) or not crop:
                                crop = row.get('cpcv2_description', 'Unknown Crop')
                            if pd.isna(crop):
                                crop = 'Unknown Crop'
                            
                            crop_set.add(crop)
                            
                            # Extract year information
                            year = None
                            if not pd.isna(row.get('season_year')):
                                try:
                                    year = int(row.get('season_year'))
                                except:
                                    # Try to extract year from dates
                                    date_fields = ['start_date', 'period_date', 'harvest_end_date']
                                    for field in date_fields:
                                        if not pd.isna(row.get(field)):
                                            try:
                                                date_str = row.get(field)
                                                # Try different date formats
                                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y']:
                                                    try:
                                                        date_obj = datetime.strptime(date_str, fmt)
                                                        year = date_obj.year
                                                        break
                                                    except:
                                                        continue
                                                if year:
                                                    break
                                            except:
                                                continue
                            
                            # Extract seasonality information
                            season = row.get('season_name', '')
                            if pd.isna(season) or not season:
                                season = row.get('season_type', 'Annual')
                            if pd.isna(season):
                                season = 'Annual'
                            
                            # Extract region information (most detailed available)
                            region = None
                            for admin_level in ['admin_4', 'admin_3', 'admin_2', 'admin_1', 'admin_0']:
                                if not pd.isna(row.get(admin_level)) and row.get(admin_level):
                                    region = row.get(admin_level)
                                    break
                            if not region:
                                region = row.get('geographic_unit_name', 'National')
                            
                            # Extract indicator and determine data availability
                            indicator = row.get('indicator', '')
                            indicator_group = row.get('indicator_group', '')
                            
                            # Determine data metrics availability
                            area_planted = False
                            area_harvested = False
                            quantity_produced = False
                            production = False
                            
                            # Use indicator information to flag availability
                            if not pd.isna(indicator):
                                indicator_lower = indicator.lower()
                                if 'planted' in indicator_lower or 'planting' in indicator_lower or 'area planted' in indicator_lower:
                                    area_planted = True
                                if 'harvested' in indicator_lower or 'harvesting' in indicator_lower or 'area harvested' in indicator_lower:
                                    area_harvested = True
                                if 'yield' in indicator_lower or 'production' in indicator_lower:
                                    production = True
                                if 'quantity' in indicator_lower or 'volume' in indicator_lower or 'output' in indicator_lower:
                                    quantity_produced = True
                            
                            # Use indicator group as fallback
                            if not (area_planted or area_harvested or quantity_produced or production) and not pd.isna(indicator_group):
                                indicator_group_lower = indicator_group.lower()
                                if 'area' in indicator_group_lower:
                                    area_planted = True
                                    area_harvested = True
                                if 'production' in indicator_group_lower:
                                    production = True
                                if 'quantity' in indicator_group_lower or 'yield' in indicator_group_lower:
                                    quantity_produced = True
                            
                            # Data source
                            source = row.get('source_organization', '')
                            if pd.isna(source) or not source:
                                source = row.get('source_document', 'Unknown')
                            if pd.isna(source):
                                source = 'Unknown'
                            
                            # Update inventory
                            if year:
                                inventory[country_code][crop]['years'].add(year)
                            
                            inventory[country_code][crop]['seasonality'].add(season)
                            inventory[country_code][crop]['area_planted'] |= area_planted
                            inventory[country_code][crop]['area_harvested'] |= area_harvested
                            inventory[country_code][crop]['quantity_produced'] |= quantity_produced
                            inventory[country_code][crop]['production'] |= production
                            
                            if region:
                                inventory[country_code][crop]['regions'].add(region)
                            
                            inventory[country_code][crop]['data_sources'].add(source)
                            
                            if not pd.isna(indicator):
                                inventory[country_code][crop]['indicators'].add(indicator)
                        except Exception as e:
                            error_count += 1
                            print(f"Error processing row: {e}")
                    
                    file_count += 1
                    if file_count % 10 == 0:
                        print(f"Processed {file_count} files, {row_count} rows with {error_count} errors")
                        print(f"Found {len(country_set)} countries and {len(crop_set)} crops so far")
                
                except Exception as e:
                    print(f"Error processing {os.path.join(dirpath, filename)}: {e}")
    
    # Convert sets to sorted lists for JSON serialization
    for country_code in inventory:
        for crop in inventory[country_code]:
            inventory[country_code][crop]['years'] = sorted(list(inventory[country_code][crop]['years']))
            inventory[country_code][crop]['seasonality'] = sorted(list(inventory[country_code][crop]['seasonality']))
            inventory[country_code][crop]['regions'] = sorted(list(inventory[country_code][crop]['regions']))
            inventory[country_code][crop]['data_sources'] = sorted(list(inventory[country_code][crop]['data_sources']))
            inventory[country_code][crop]['indicators'] = sorted(list(inventory[country_code][crop]['indicators']))
    
    # Print summary statistics
    print(f"Completed processing {file_count} files, {row_count} rows with {error_count} errors")
    print(f"Final inventory contains {len(inventory)} countries and {sum(len(crops) for crops in inventory.values())} crop entries")
    
    return dict(inventory)

def create_summary_dataframe(inventory):
    """
    Create a summary dataframe from the inventory.
    """
    records = []
    
    for country_code, crops in inventory.items():
        for crop_name, info in crops.items():
            # Get a list of available indicators
            indicators_available = []
            if info['area_planted']:
                indicators_available.append('Area Planted')
            if info['area_harvested']:
                indicators_available.append('Area Harvested')
            if info['quantity_produced']:
                indicators_available.append('Quantity Produced')
            if info['production']:
                indicators_available.append('Production')
            
            # Create a record for each country-crop combination
            record = {
                'country_code': country_code,
                'crop': crop_name,
                'year_count': len(info['years']),
                'year_min': min(info['years']) if info['years'] else None,
                'year_max': max(info['years']) if info['years'] else None,
                'year_range': f"{min(info['years'])}-{max(info['years'])}" if info['years'] else "N/A",
                'years': info['years'],  # Add the full list of years
                'seasonality': ', '.join(info['seasonality']) if info['seasonality'] else "N/A",
                'region_count': len(info['regions']),
                'has_area_planted': info['area_planted'],
                'has_area_harvested': info['area_harvested'],
                'has_quantity': info['quantity_produced'],
                'has_production': info['production'],
                'indicators_available': ', '.join(indicators_available),
                'completeness': sum([
                    info['area_planted'], 
                    info['area_harvested'], 
                    info['quantity_produced'], 
                    info['production']
                ]) / 4.0 * 100,  # Keep this for filtering
                'data_sources': '; '.join(info['data_sources']) if len(info['data_sources']) <= 3 else f"{len(info['data_sources'])} sources",
                'indicator_count': len(info['indicators'])
            }
            records.append(record)
    
    return pd.DataFrame(records)

def load_country_mapping(mapping_file=None):
    """
    Load country mapping from CSV file or use a fallback.
    
    Parameters:
    -----------
    mapping_file : str, optional
        Path to the country codes CSV file
    
    Returns:
    --------
    dict
        Mapping of country codes to country names
    """
    # Start with an empty mapping
    mapping = {}
    
    # Try to load from CSV if file is provided
    if mapping_file and os.path.exists(mapping_file):
        try:
            df = pd.read_csv(mapping_file)
            print(f"Loaded country mapping file with columns: {df.columns.tolist()}")
            
            # Create ISO3 mapping
            if 'ISO2_Code' in df.columns and 'ISO3_Code' in df.columns:
                for _, row in df.iterrows():
                    if not pd.isna(row['ISO2_Code']) and not pd.isna(row['ISO3_Code']):
                        mapping[row['ISO2_Code']] = row['ISO3_Code']
                
                print(f"Created mapping for {len(mapping)} countries")
            
            # Also create a mapping from country codes to names
            country_name_mapping = {}
            if 'ISO3_Code' in df.columns and 'Country_Name' in df.columns:
                for _, row in df.iterrows():
                    if not pd.isna(row['ISO3_Code']) and not pd.isna(row['Country_Name']):
                        country_name_mapping[row['ISO3_Code']] = row['Country_Name']
        except Exception as e:
            print(f"Error processing country mapping file: {e}")
    
    # Try to supplement with pycountry if available
    try:
        import pycountry
        for country in pycountry.countries:
            if hasattr(country, 'alpha_3') and country.alpha_3:
                if country.alpha_3 not in mapping:
                    mapping[country.alpha_3] = country.name
    except ImportError:
        print("Warning: pycountry not available for additional country mappings")
    
    # Add a fallback for common countries if the mapping is empty
    if not mapping:
        mapping = {
            'USA': 'United States',
            'CAN': 'Canada',
            'MEX': 'Mexico',
            'BRA': 'Brazil',
            'ARG': 'Argentina',
            'CHN': 'China',
            'IND': 'India',
            'JPN': 'Japan',
            'GBR': 'United Kingdom',
            'FRA': 'France',
            'DEU': 'Germany',
        }
        print("Using fallback country mapping")
    
    return mapping