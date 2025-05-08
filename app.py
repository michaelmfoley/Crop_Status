import os
import dash

# Import dashboard creation function
from crop_inventory.dashboard import create_dashboard

# Get the path to the data files
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, "data")

# Create the dashboard app
app = create_dashboard(
    inventory_json_path=os.path.join(data_dir, "crop_inventory.json"),
    summary_csv_path=os.path.join(data_dir, "crop_inventory_summary.csv"),
    country_mapping_file=os.path.join(data_dir, "country_codes_with_iso3.csv"),
    country_summary_path=os.path.join(data_dir, "country_summary.csv")
)

# Expose the server for gunicorn - needed for deployment platforms
server = app.server

if __name__ == "__main__":
    # Use environment variable for port (required by hosting platforms)
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)