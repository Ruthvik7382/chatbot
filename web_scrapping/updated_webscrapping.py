# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import zipfile
import os
from tqdm import tqdm
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin

import pandas as pd
os.chdir('/home/ec2-user/ITMT597/misc/files/urls_split')

academic_programs = pd.read_csv('academic_programs.csv')
student_service = pd.read_csv('student_service.csv')
admissions_and_enrollment = pd.read_csv('admissions_and_enrollment.csv')
admin_policy_info = pd.read_csv('admin_policy_info.csv')
specialized_programs = pd.read_csv('specialized_programs.csv')

def remove_commas_and_save(input_file):
    try:
        with open(input_file, 'r') as infile:
            content = infile.read()
            content_without_commas = content.replace(',', '')

        with open(input_file, 'w') as outfile:
            outfile.write(content_without_commas)
            return input_file


    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")

# Function for running through bulletin URL's
def extract_data_and_save_b(url):

    retry_strategy = Retry(
    total=8,  # Number of maximum retries
    backoff_factor=1,  # Exponential backoff factor
    status_forcelist=[500, 502, 503, 504],  # HTTP status codes to retry on
    )

    # Create an HTTP session with retry settings
    http = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http.mount("http://", adapter)
    http.mount("https://", adapter)


    try:
    # Send a GET request using the HTTP session
    #here 5 sec is connection_timeout where 27 sec is read time_out once the connection is established
        response = requests.get(url, timeout=(5, 27))

        # Empty dictionary for storing headers and tables
        data = {}

        sos_added = True

        if response.status_code == 200:

            soup = BeautifulSoup(response.text, 'html.parser')

            heading_text = None

            # Find all relevant elements within <main>
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table','ul','div']):
                tag_name = element.name

                if tag_name == 'h1':
                    heading_text1 = element.text.strip()
                    if heading_text1:
                        main_heading = heading_text1



                if tag_name.startswith('h'):
                    heading_text = element.text.strip()
                    previous_heading = heading_text
                    if heading_text:
                        if sos_added:
                            if tag_name == 'h1':
                                heading_text = f'sos: {heading_text}'
                            else:
                                if main_heading is None:
                                    main_heading = 'Academic Programs Details'
                                heading_text = f'sos: {main_heading} <{heading_text}>'
                        data[heading_text] = []


                elif tag_name == 'p':
                    if heading_text:
                        passage_text = element.text.strip()
                        data[heading_text].append(passage_text)


                elif tag_name == 'ul':
                    list_data = []
                    for li in element.find_all('li'):
                        bullet_point = li.text.strip()
                        list_data.append(bullet_point)

                    if heading_text:
                        data[heading_text].extend(list_data)


                elif tag_name == 'table':
                    table_data = []
                    a = False
                    for row in element.find_all('tr'):
                        row_data = [cell.text.strip() for cell in row.find_all(['th', 'td'])]
                        if row_data == ['Year 1']:
                            new_data = []
                            new_data.append(row_data)  # Start a new list when 'Year 1' is encountered
                            a = True
                        elif a:
                            new_data.append(row_data)  # Append subsequent rows to the new list
                        else:
                            table_data.append(row_data)
                    if a:
                        data1 = new_data
                        last_item = data1[-1]
                        columns = data1[1]
                        df1 = pd.DataFrame(data1, columns=columns)

                        year_word = None
                        for index, row in df1.iterrows():
                            if row[columns[0]].startswith('Year'):
                                year_word = row[columns[0]]

                            elif row[columns[0]].startswith('Semester'):
                                df1.at[index, columns[0]] = f'{year_word}\n{row[columns[0]]}'
                                df1.at[index, columns[2]] = f'{year_word}\n{row[columns[2]]}'

                        df1 = df1.replace('None', pd.NA).dropna()
                        new_df = df1.iloc[:, -2:]
                        df1 = df1.iloc[:, :2]
                        column_names = df1.columns
                        new_df.columns = column_names
                        result_df = pd.concat([df1, new_df], axis=0)
                        result_list_of_lists = result_df.values.tolist()
                        result_list_of_lists.append(last_item)
                        for item in result_list_of_lists:
                            table_data.append(item)
                    if heading_text:
                        if any(char.isalpha() for char in 'table_data[0][0]') and any(char.isdigit() for char in 'table_data[0][0]'):
                            intro_text = f"These are the {previous_heading} courses for the {main_heading}"
                            table_data.insert(0, [intro_text.replace("sos: ", "")])
                            #table_data.pop(1)
                            data[heading_text].append(table_data)
                        else:
                            intro_text = f"These are the {table_data[0][0]} for the {main_heading} {heading_text} and the total credits are {table_data[0][1]}"
                            table_data.insert(0, [intro_text.replace("sos: ", "")])
                            #table_data.pop(2)
                            table_data.pop(1)
                            data[heading_text].append(table_data)

                elif tag_name == 'div' and 'courseblock' in element.get('class', []):
                    course_code_elem = element.find(class_='coursecode')
                    course_title_elem = element.find(class_='coursetitle')
                    course_attrs_elem = element.find(class_='noindent courseblockattr hours')
                    satisfies_elem = element.find(class_='noindent courseblockattr')

                    # Check if elements are found before accessing their text attributes
                    course_code = course_code_elem.text.strip() if course_code_elem else ''
                    data[heading_text].append(course_code)
                    course_title = course_title_elem.text.strip() if course_title_elem else ''
                    data[heading_text].append(course_title)
                    course_attrs = course_attrs_elem.get_text(" ",strip=True) if course_attrs_elem else ''
                    data[heading_text].append(course_attrs)
                    satisfies = satisfies_elem.get_text(" ",strip=True) if satisfies_elem else ''
                    data[heading_text].append(satisfies)

                elif tag_name == 'div' and 'cl-menu' in element.get('id', ''):
                    break


            output_file_path = f'{url_hash}.txt'

        else:
            print(f"Failed to retrieve URL: {url[0]}. Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error while fetching URL: {url[0]}. Exception: {e}")


  # Find all relevant elements
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for heading, content in data.items():
            output_file.write(f"{heading}\n")
            for item in content:
                if isinstance(item, str):
                    output_file.write(f"{item}\n")
                elif isinstance(item, list):
                    for row in item:
                        output_file.write(f"{', '.join(row)}\n")
            output_file.write(f"Information Source: {url}\n\n")

    final_output = remove_commas_and_save(output_file_path)

# Function for running through IIT URL's
def extract_data_and_save(url):

    retry_strategy = Retry(
    total=8,  # Number of maximum retries
    backoff_factor=1,  # Exponential backoff factor
    status_forcelist=[500, 502, 503, 504],  # HTTP status codes to retry on
    )

    # Create an HTTP session with retry settings
    http = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http.mount("http://", adapter)
    http.mount("https://", adapter)


    try:
    # Send a GET request using the HTTP session
    #here 5 sec is connection_timeout where 27 sec is read time_out once the connection is established
        response = requests.get(url, timeout=(5, 27))

        # Empty dictionary for storing headers and tables
        data = {}

        sos_added = True

        if response.status_code == 200:

            soup = BeautifulSoup(response.text, 'html.parser')

            main = soup.find('main')

            if main:
                first_heading = None
                heading_text = None

                # Find all relevant elements within <main>
                for element in main.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table', 'ul','div']): #removed 'a'

                    if element.find_parent('nav'):
                        continue

                    tag_name = element.name

                    if tag_name.startswith('h'):
                        heading_text = element.text.strip()
                        if heading_text:
                            if first_heading is None:
                                first_heading = f'sos: {heading_text}'
                                data[heading_text] = []
                            else:
                                data[heading_text] = []

                    elif tag_name == 'p':
                        if heading_text:
                            passage_text = element.text.strip()
                            if heading_text not in data:
                                data[heading_text] = []
                            data[heading_text].append(passage_text)

                    elif tag_name == 'ul':
                        list_data = []
                        for li in element.find_all('li'):
                            bullet_point = li.text.strip()
                            list_data.append(bullet_point)

                        if heading_text:
                            data[heading_text].extend(list_data)

                    elif tag_name == 'table':
                        table_data = []
                        for row in element.find_all('tr'):
                            row_data = [cell.text.strip() for cell in row.find_all('td')]
                            table_data.append(row_data)
                        if heading_text:
                            data[heading_text].append(table_data)

                    elif tag_name == 'span' and 'profile-item__contact__item' in element.get('class', []):
                        # Extract data from the location element
                        info_type = element.find('i')
                        if info_type:
                            info_type = info_type['class'][1]
                            info_text = element.get_text(strip=True)
                            last_word = element['class'][-1]
                            data[heading_text].append(f'{last_word}: {info_text}')

                if first_heading:
                    modified_data = {}
                    for key in data:
                        if key != first_heading:
                            modified_key = f'{first_heading} <{key}>'
                            modified_data[modified_key] = data[key]
                        else:
                            modified_data[first_heading] = data[key]

                #    return first_heading, modified_data

                #combined_data = '\n'.join(map(str, data))

                output_file_path = f'{url_hash}.txt'

        else:
            print(f"Failed to retrieve URL: {url[0]}. Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error while fetching URL: {url[0]}. Exception: {e}")


  # Find all relevant elements
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for heading, content in modified_data.items():
            output_file.write(f"{heading}\n")
            for item in content:
                if isinstance(item, str):
                    output_file.write(f"{item}\n")
                elif isinstance(item, list):
                    for row in item:
                        output_file.write(f"{', '.join(row)}\n")
            output_file.write(f"Information Source: {url}\n\n")


""" elif tag_name == 'a':
    link_text = element.text.strip()
    link_href = element.get('href')
    if link_href:
        # Check if the href is an absolute URL or a relative URL
        if link_href.startswith("http://") or link_href.startswith("https://"):
            cleaned_link = link_href
        else:
            # If it's a relative URL, convert it to absolute by joining with the base URL
            cleaned_link = urljoin(url, link_href)
    else:
        cleaned_link = None  # Handle cases where href is missing

    if heading_text and link_text and cleaned_link is not None:
        data[heading_text].append(f'Link: {link_text} {cleaned_link}')"""

##webscrapping academic programs urls

#creating df object that would contain all the urls
df = academic_programs

#list for url & hash mapping
list_urls=[]

os.chdir('/home/ec2-user/ITMT597/misc/files/urls_split/academic_programs')
print(os.getcwd())

#iterating over each of the URLs for webscrapping
for index, row in tqdm(df.iterrows()):
    url = row['urls']
    url_hash = hash(url)

    # Extract data from the current URL and save it to a text file
    extract_data_and_save_b(url)

    #URL and URL_hash mapping
    list_urls.append([url, url_hash])


    # Add the text file to the zip archive
    #zip_file.write(f'extracted_data_{url_hash}.txt', os.path.join(output_dir, f'extracted_data_{url_hash}.txt'))

df_url = pd.DataFrame(list_urls, columns=['url', 'hash'])
df_url.to_csv('url_mapping.csv')

##now combining all the text files into one file
directory_path = '/home/ec2-user/ITMT597/misc/files/urls_split/academic_programs'
# Specify the name of the output combined file
output_file_name = 'combined_academic_programs.txt'

# Create a list to store the content of each file
file_contents = []

# Loop through all .txt files in the directory

for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)

        # Open and read the content of each .txt file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents.append(file.read())

# Combine the contents of all files into one string
combined_text = '\n'.join(file_contents)

# Write the combined text to the output file
output_file_path = os.path.join(directory_path, output_file_name)
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_text)

print(f"Combined text saved to {output_file_path}")

df = student_service

#list for url & hash mapping
list_urls=[]

os.chdir('/home/ec2-user/ITMT597/misc/files/urls_split/student_service')
print(os.getcwd())

#iterating over each of the URLs for webscrapping
for index, row in tqdm(df.iterrows()):
    url = row['urls']
    url_hash = hash(url)

    # Extract data from the current URL and save it to a text file
    extract_data_and_save(url)

    #URL and URL_hash mapping
    list_urls.append([url, url_hash])


    # Add the text file to the zip archive
    #zip_file.write(f'extracted_data_{url_hash}.txt', os.path.join(output_dir, f'extracted_data_{url_hash}.txt'))

df_url = pd.DataFrame(list_urls, columns=['url', 'hash'])
df_url.to_csv('url_mapping.csv')

##now combining all the text files into one file
directory_path = '/home/ec2-user/ITMT597/misc/files/urls_split/student_service'
# Specify the name of the output combined file
output_file_name = 'combined_student_service.txt'

# Create a list to store the content of each file
file_contents = []

# Loop through all .txt files in the directory

for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)

        # Open and read the content of each .txt file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents.append(file.read())

# Combine the contents of all files into one string
combined_text = '\n'.join(file_contents)

# Write the combined text to the output file
output_file_path = os.path.join(directory_path, output_file_name)
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_text)

print(f"Combined text saved to {output_file_path}")

df = admissions_and_enrollment

#list for url & hash mapping
list_urls=[]

os.chdir('/home/ec2-user/ITMT597/misc/files/urls_split/admissions_and_enrollment')


#iterating over each of the URLs for webscrapping
for index, row in tqdm(df.iterrows()):
    url = row['urls']
    url_hash = hash(url)

    # Extract data from the current URL and save it to a text file
    extract_data_and_save(url)

    #URL and URL_hash mapping
    list_urls.append([url, url_hash])


    # Add the text file to the zip archive
    #zip_file.write(f'extracted_data_{url_hash}.txt', os.path.join(output_dir, f'extracted_data_{url_hash}.txt'))

df_url = pd.DataFrame(list_urls, columns=['url', 'hash'])
df_url.to_csv('url_mapping.csv')

##now combining all the text files into one file
directory_path = '/home/ec2-user/ITMT597/misc/files/urls_split/admissions_and_enrollment'
# Specify the name of the output combined file
output_file_name = 'combined_admissions_and_enrollment.txt'

# Create a list to store the content of each file
file_contents = []

# Loop through all .txt files in the directory

for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)

        # Open and read the content of each .txt file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents.append(file.read())

# Combine the contents of all files into one string
combined_text = '\n'.join(file_contents)

# Write the combined text to the output file
output_file_path = os.path.join(directory_path, output_file_name)
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_text)

print(f"Combined text saved to {output_file_path}")

df = admin_policy_info.iloc[0:43,:]
df2 = admin_policy_info.iloc[43:-1,:]

#list for url & hash mapping
list_urls=[]

os.chdir('/home/ec2-user/ITMT597/misc/files/urls_split/admin_policy_info')
print(os.getcwd())

#iterating over each of the URLs for webscrapping
for index, row in tqdm(df.iterrows()):
    url = row['urls']
    url_hash = hash(url)

    # Extract data from the current URL and save it to a text file
    extract_data_and_save(url)

    #URL and URL_hash mapping
    list_urls.append([url, url_hash])


    # Add the text file to the zip archive
    #zip_file.write(f'extracted_data_{url_hash}.txt', os.path.join(output_dir, f'extracted_data_{url_hash}.txt'))

df_url = pd.DataFrame(list_urls, columns=['url', 'hash'])
df_url.to_csv('url_mapping.csv')

list_urls2=[]
for index, row in tqdm(df2.iterrows()):
    url = row['urls']
    url_hash = hash(url)

    # Extract data from the current URL and save it to a text file
    extract_data_and_save_b(url)

    #URL and URL_hash mapping
    list_urls2.append([url, url_hash])


    # Add the text file to the zip archive
    #zip_file.write(f'extracted_data_{url_hash}.txt', os.path.join(output_dir, f'extracted_data_{url_hash}.txt'))

df_url2 = pd.DataFrame(list_urls2, columns=['url', 'hash'])
df_url2.to_csv('url_mapping2.csv')

##now combining all the text files into one file
directory_path = '/home/ec2-user/ITMT597/misc/files/urls_split/admin_policy_info'
# Specify the name of the output combined file
output_file_name = 'combined_admin_policy_info.txt'

# Create a list to store the content of each file
file_contents = []

# Loop through all .txt files in the directory

for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)

        # Open and read the content of each .txt file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents.append(file.read())

# Combine the contents of all files into one string
combined_text = '\n'.join(file_contents)

# Write the combined text to the output file
output_file_path = os.path.join(directory_path, output_file_name)
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_text)

print(f"Combined text saved to {output_file_path}")

df = specialized_programs

#list for url & hash mapping
list_urls=[]

os.chdir('/home/ec2-user/ITMT597/misc/files/urls_split/specialized_programs')


#iterating over each of the URLs for webscrapping
for index, row in tqdm(df.iterrows()):
    url = row['urls']
    url_hash = hash(url)

    # Extract data from the current URL and save it to a text file
    extract_data_and_save(url)

    #URL and URL_hash mapping
    list_urls.append([url, url_hash])


    # Add the text file to the zip archive
    #zip_file.write(f'extracted_data_{url_hash}.txt', os.path.join(output_dir, f'extracted_data_{url_hash}.txt'))

df_url = pd.DataFrame(list_urls, columns=['url', 'hash'])
df_url.to_csv('url_mapping.csv')

##now combining all the text files into one file
directory_path = '/home/ec2-user/ITMT597/misc/files/urls_split/specialized_programs'
# Specify the name of the output combined file
output_file_name = 'combined_specialized_programs.txt'

# Create a list to store the content of each file
file_contents = []

# Loop through all .txt files in the directory

for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)

        # Open and read the content of each .txt file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents.append(file.read())

# Combine the contents of all files into one string
combined_text = '\n'.join(file_contents)

# Write the combined text to the output file
output_file_path = os.path.join(directory_path, output_file_name)
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_text)

print(f"Combined text saved to {output_file_path}")

# Define the file path
file_path1 ='/home/ec2-user/ITMT597/misc/files/urls_split/admin_policy_info/combined_admin_policy_info.txt'
file_path2 ='/home/ec2-user/ITMT597/misc/files/urls_split/admissions_and_enrollment/combined_admissions_and_enrollment.txt'
file_path3 ='/home/ec2-user/ITMT597/misc/files/urls_split/student_service/combined_student_service.txt'
file_path4 ='/home/ec2-user/ITMT597/misc/files/urls_split/specialized_programs/combined_specialized_programs.txt'

# Text to be removed
text_to_remove = "sos: Print Options\nPrint this page.\nThe PDF will include all information unique to this page."

paths = [file_path1, file_path2, file_path3, file_path4]

for file_path in paths:
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    # Replace the unwanted text with an empty string
    modified_content = file_content.replace(text_to_remove, '')

    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

    print("Text removed successfully.")

##creating no split text file
directory_path = '/home/ec2-user/ITMT597/misc/files/urls_split/no_split_data'
# Specify the name of the output combined file
output_file_name = 'combined_all.txt'

# Create a list to store the content of each file
file_contents = []

# Loop through all .txt files in the directory

for filename in os.listdir(directory_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(directory_path, filename)

        # Open and read the content of each .txt file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents.append(file.read())

# Combine the contents of all files into one string
combined_text = '\n'.join(file_contents)

# Write the combined text to the output file
output_file_path = os.path.join(directory_path, output_file_name)
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(combined_text)

print(f"Combined text saved to {output_file_path}")
