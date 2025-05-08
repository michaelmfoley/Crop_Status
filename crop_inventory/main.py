import os
import argparse
import sys
import pandas as pd
import json
from pathlib import Path

def main():
    """Main function to run the crop data inventory process."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Create and visualize a crop data inventory')
    parser.add_argument('--data_dir', type=str, required=True, help='Root directory of the M49 database')
    parser.add_argument('--output_dir', type=str, default='data', help='Directory to store output files')
    parser.add_argument('--country_mapping', type=str, help='Path to country codes CSV file')
    parser.add_argument('--port', type=int, default=8050, help='Port for the Dash server')
    parser.add_argument('--skip_processing', action='store_true', help='Skip data processing and use existing inventory files')
    
    args = parser.parse_args()
    
    # Validate data directory
    if not os.path.isdir(args.data_dir):
        print(f"Error: Data directory '{args.data_dir}' does not exist")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Define output paths
    inventory_path = os.path.join(args.output_dir, "crop_inventory.json")
    summary_path = os.path.join(args.output_dir, "crop_inventory_summary.csv")
    country_summary_path = os.path.join(args.output_dir, "country_summary.csv")
    
    # Process data if needed
    if args.skip_processing and os.path.exists(inventory_path) and os.path.exists(summary_path):
        print(f"Using existing inventory files from {args.output_dir}")
    else:
        # Import processing functions
        try:
            from crop_inventory.inventory_utils import create_crop_inventory, create_summary_dataframe, load_country_mapping
        except ImportError:
            try:
                from inventory_utils import create_crop_inventory, create_summary_dataframe, load_country_mapping
            except ImportError as e:
                print(f"Error importing required modules: {e}")
                print("Make sure inventory_utils.py is in the current directory or in the crop_inventory package")
                sys.exit(1)
            
        # Create the inventory
        print(f"Creating crop inventory from {args.data_dir}...")
        try:
            inventory = create_crop_inventory(args.data_dir)
            
            # Save to file
            with open(inventory_path, 'w') as f:
                json.dump(inventory, f, indent=2)
            print(f"Inventory saved to {inventory_path}")
            
            # Create summary dataframe
            summary_df = create_summary_dataframe(inventory)
            
            # Save summary to CSV
            summary_df.to_csv(summary_path, index=False)
            print(f"Summary saved to {summary_path}")
            
            # Additional: Save country-level summary
            country_summary = summary_df.groupby('country_code').agg({
                'crop': 'nunique',
                'year_min': 'min',
                'year_max': 'max',
                'region_count': 'sum',
                'completeness': 'mean'
            }).reset_index()
            
            # Get country names
            country_mapping = load_country_mapping(args.country_mapping)
            country_summary['country_name'] = country_summary['country_code'].map(
                lambda x: country_mapping.get(x, f"Country {x}")
            )
            
            country_summary.to_csv(country_summary_path, index=False)
            print(f"Country summary saved to {country_summary_path}")
        
        except Exception as e:
            print(f"Error processing crop data: {e}")
            sys.exit(1)
    
    # Create and run the dashboard
    try:
        from crop_inventory.dashboard import create_dashboard
        
        print("Starting dashboard...")
        app = create_dashboard(
            inventory_json_path=inventory_path, 
            summary_csv_path=summary_path, 
            country_mapping_file=args.country_mapping,
            country_summary_path=country_summary_path
        )
        
        # Run the server
        print(f"Dashboard running at http://localhost:{args.port}")
        print("Press Ctrl+C to stop the server")
        app.run(debug=True, port=args.port, host='0.0.0.0')
    except ImportError:
        try:
            from dashboard import create_dashboard
            # Rest of code same as above
            print("Starting dashboard...")
            app = create_dashboard(
                inventory_json_path=inventory_path, 
                summary_csv_path=summary_path, 
                country_mapping_file=args.country_mapping,
                country_summary_path=country_summary_path
            )
            
            # Run the server
            print(f"Dashboard running at http://localhost:{args.port}")
            print("Press Ctrl+C to stop the server")
            app.run(debug=True, port=args.port, host='0.0.0.0')
        except ImportError as e:
            print(f"Error importing dashboard module: {e}")
            print("Make sure dashboard.py is in the current directory or in the crop_inventory package")
            sys.exit(1)
    except Exception as e:
        print(f"Error running dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()