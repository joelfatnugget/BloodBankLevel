import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Function to fetch blood levels
def fetch_blood_levels():
    url = "https://redcross.sg/"  # Replace with the actual URL
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        blood_elements = soup.find_all(class_="blood-grp-text")

        blood_levels = {}
        for element in blood_elements:
            blood_type = element.find("h3").text.strip()
            blood_level = element.find("h5").text.strip()
            blood_levels[blood_type] = blood_level
        print(blood_levels)
        return blood_levels
    else:
        raise Exception(f"Failed to fetch the webpage. Status code: {response.status_code}")

# Function to write blood levels to Markdown
def write_to_markdown(blood_levels):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("blood_levels.md", "w") as file:
        # Header
        file.write("# Blood Levels Status\n\n")
        file.write(f"**Last Updated**: {current_time}\n\n")
        file.write("## Blood Levels Overview\n\n")
        
        # Table format
        file.write("| Blood Type | Status         |\n")
        file.write("|------------|----------------|\n")
        for blood_type, level in blood_levels.items():
            file.write(f"| {blood_type}      | {level} |\n")

# Main script execution
if __name__ == "__main__":
    blood_levels = fetch_blood_levels()
    write_to_markdown(blood_levels)
