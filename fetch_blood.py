import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

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
    sg_timezone = pytz.timezone("Asia/Singapore")
    current_time = datetime.now(sg_timezone)
    formatted_time = current_time.strftime("%d %b %Y %H:%M:%S GMT+8")
    markdown_content = "Singapore Blood Levels\n Please donate to the Blood Bank if you are able to do so!"
    markdown_content += "\n================================================================================================================================"
    markdown_content += f"\n\n### Blood Levels (Updated: {formatted_time})\n"
    markdown_content += "| Blood Type | Level     |\n"
    markdown_content += "|------------|-----------|\n"
    for blood_type, level in blood_levels.items():
        markdown_content += f"| {blood_type}     | {level} |\n"
    with open("README.md", "w") as file:
       file.write(markdown_content)
# Main script execution
if __name__ == "__main__":
    blood_levels = fetch_blood_levels()
    write_to_markdown(blood_levels)
