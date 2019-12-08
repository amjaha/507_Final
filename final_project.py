import requests
import os
from bs4 import BeautifulSoup as bs
import json
import pprint
import plotly
import plotly.graph_objs as go
import numpy as np
import webbrowser
from jinja2 import Template
from flask import Flask, render_template
from sqlalchemy_utils import database_exists
from sqlalchemy import Column, Integer, String, Float, ForeignKey, func, and_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from secrets import google_places_key
from secrets import mapbox_key

### CACHING ###

# caching html from individual university pages
try:
    cache_file = open('university_htmls.txt', 'r')
    cache_contents = cache_file.read()
    UNIVERSITIES = json.loads(cache_contents)
    cache_file.close()
except:
    UNIVERSITIES = {}

# caching results from google places search
try:
    cache_file = open('google_places.txt', 'r')
    cache_contents = cache_file.read()
    GOOGLE_PLACES = json.loads(cache_contents)
    cache_file.close()
except:
    GOOGLE_PLACES = {}

# caching links from individual university pages in a list for efficient looping
try:
    cache_file = open('links_list.txt', 'r')
    cache_contents = cache_file.read()
    UNIVERSITY_LIST = list(json.loads(cache_contents))
    cache_file.close()
except:
    UNIVERSITY_LIST = []

### CLASSES ###

# creating classes connected to database tables with sqlalchemy

Base = declarative_base() 

class University(Base):
    __tablename__ = 'University'
    name = Column(String(32), primary_key = True)
    acceptance = Column(Float)
    tuition = Column(Float)
    gpa = Column(Float)
    degree = relationship('Major', back_populates = 'university')
    location = relationship('Location', back_populates = 'university')
    lat = Column(Float)
    lng = Column(Float)

    def __init__(self, name, acceptance, tuition, gpa, lat, lng):
        self.name = name
        self.acceptance = acceptance
        self.tuition = tuition
        self.gpa = gpa
        self.lat = lat
        self.lng = lng


class Major(Base):
    __tablename__ = 'Major'
    name = Column(String(32), ForeignKey('University.name'))
    major = Column(String(32))
    id = Column(Integer, primary_key = True, autoincrement = True)
    university = relationship('University', back_populates = 'degree')
    
    def __init__(self, name, major):
        self.name = name
        self.major = major


class Location(Base):
    __tablename__ = 'Location'
    name = Column(String(32), ForeignKey('University.name'), primary_key = True)
    address = Column(String(64))
    city = Column(String(32))
    state = Column(String(32))
    zip_code = Column(String(32))
    university = relationship('University', back_populates = 'location')

    def __init__(self, name, address, city, state, zip_code):
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code

### COLLECTING DATA ###

# collects the urls and html for university sites from Princeton Review's browse pages
# takes int argument and returns dict of university pages collected for testing
def get_start_sites(num_pages = 11):
    # start page link
    link = 'https://www.princetonreview.com/college-search'
    pages = {}
    for i in range(num_pages): 
        # get start page and create soup
        html = requests.get(link).text
        soup = bs(html, 'html.parser')
        # use soup to get university links and html and adds to dict
        pages.update(get_university_sites(soup))
        # finds next link to collect more universities
        next_parent = soup.find_all(name = 'ul', attrs={'class' : 'pagination'})
        next_child = next_parent[0].find_all(name = 'a')
        next = next_child[-1]['href']
        link = 'https://www.princetonreview.com/' + next
    # returns pages for testing 
    return pages

# takes browse page as argument, finds links and html for university sites and returns as a dict for testing
def get_university_sites(soup):
    link_list = []
    local_links = {}
    # finding university-specific part of link
    parent_class = soup.find_all(name = 'div', attrs={'class' : 'col-md-3'})
    child_class = soup.find_all(name = 'a')
    for response in child_class:
        try:
            link = response['href']
            try:
                if link[0] == '/' and link[-6].isnumeric() and link not in link_list:
                    link_list.append(link)
            except(IndexError):
                pass
        except(KeyError):
            pass
    # appending university link portion to base, adding to list, and grabbing html
    base = 'https://www.princetonreview.com'
    for university in link_list:
        link = base + university
        # appends pages to university_list
        if link in UNIVERSITY_LIST:
            pass
        else:
            UNIVERSITY_LIST.append(link)
        # adds pages to cache
        if link in UNIVERSITIES:
            pass
        else:
            html = requests.get(link).text
            UNIVERSITIES[link] = html
        # gets sub-pages for each university
        link, html = get_next_university_links(link)
        local_links[link] = html
    # returns local_links dict for testing
    return local_links

# takes a university link, returns links and html for testing
def get_next_university_links(link):
    # creates sub_pages links
    academics = link + '#!academics'
    tuition = link + '#!tuition'
    student_body = link + '#!studentbody'
    visit = link + '#!visiting'
    links = [academics, tuition, student_body, visit]
    # adds sub-pages to cache
    for link in links:
        if link in UNIVERSITIES:
            pass
        else:
            html = requests.get(link).text
            UNIVERSITIES[link] = html
    # returns link and html for testing
    return link, UNIVERSITIES[link]
    
# takes base university link, returns name, gpa, and acceptance rate
def get_admissions_data(link):
    soup = bs(requests.get(link).text, 'html.parser')
    parent_class = soup.find_all(name = 'div', attrs={'class' : 'number-callout'})
    name = soup.find(name = 'span', attrs = {'itemprop' : 'name'}).text
    # getting acceptance rate and converting to decimal
    acceptance_rate = parent_class[1].text.strip('%')
    acceptance_rate = float(acceptance_rate)
    # getting gpa using different method
    parent_class = soup.find_all(name = 'div', attrs = {'class' : 'row'})
    # 0.0 as default
    average_gpa = 0.0
    for row in parent_class:
        if row.find(name = 'h4'):
            if row.find(name = 'h4').text == 'Overview':
                child_class = row.find_all(name = 'div', attrs = {'class' : 'col-sm-4'})
                for item in child_class:
                    if item.find(name = 'div', attrs = {'class' : 'bold'}).text == 'Average HS GPA':
                        average_gpa = item.find(name = 'div', attrs={'class':'number-callout'}).string
    return acceptance_rate, average_gpa, name

# takes base university link, returns list of majors
def get_academics_data(link):
    link += '#!academics'
    soup = bs(UNIVERSITIES[link], 'html.parser')
    parent_class = soup.find_all(name = 'ul', attrs={'class' : 'list-unstyled'})
    major_list = []
    for i in range(len(parent_class)):
        majors = parent_class[i].find_all(name = 'h6')
        for major in majors:
            dirty_text = major.text
            text = dirty_text[1:][:-1]
            major_list.append(text)
    return major_list

# takes base university link, returns address components
def get_visit_data(link):
    link += '#!visiting'
    soup = bs(UNIVERSITIES[link], 'html.parser')
    parent_class = soup.find_all(name = 'div', attrs = {'class' : 'row'})
    for item in parent_class:
        try:
            street_address = item.find(name = 'span', attrs = {'itemprop' : 'streetAddress'}).text.strip()
        except(AttributeError):
            street_address = None
        try:
            city = item.find(name = 'span', attrs = {'itemprop' : 'addressLocality'}).text.strip()
        except(AttributeError):
            city = None
        try:
            state = item.find(name = 'span', attrs = {'itemprop' : 'addressRegion'}).text.strip()
        except(AttributeError):
            state = None
        try:
            zip_code = item.find(name = 'span', attrs = {'itemprop' : 'postalCode'}).text.strip()
        except(AttributeError):
            zip_code = None     
        if zip_code != None and state != None and city != None and street_address != None:
            break
    return street_address, city, state, zip_code

# takes base university link, returns tuition
def get_tuition_data(link):
    link += '#!tuition'
    soup = bs(UNIVERSITIES[link], 'html.parser')
    parent_class = soup.find_all(name = 'div', attrs = {'class' : 'row'})
    for row in parent_class:
        if row.find(name = 'h4'):
            if row.find(name = 'h4').text == 'Expenses per Academic Year':
                # getting tuition and converting to decimal
                try:
                    tuition = row.find(name = 'div', attrs={'class':'number-callout'}).string.replace(',', '').strip('$')
                    tuition = float(tuition)
                # 0.0 as default
                except(AttributeError):
                    tuition = 0.0
                return tuition

    return 0.0

# takes university object and returns coordinates
def get_coordinates_for_university(university):
    # construct url
    base_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json?'
    input = university.replace('--', '+')
    input = input.replace('-', '+')
    input = input.replace(' ', '+')
    input_type = 'textquery'
    field = 'location,name'
    key = google_places_key
    url = base_url + 'input=' + input + '&inputtype=' + input_type + '&fields=' + field + '&key=' + key
    page = None
    # use cache to get data
    if url in GOOGLE_PLACES:
        page = GOOGLE_PLACES[url]
    else:
        page = requests.get(url).text
        GOOGLE_PLACES[url] = page
    # isolate lat and lng
    dict = json.loads(page)
    # if no results, return empty
    if len(dict['results']) == 0:
        return None, None
    # checking accuracy of results
    result = dict['results'][0]
    try:
        lat = result['geometry']['location']['lat']
        lng = result['geometry']['location']['lng']
        return lat, lng
    except(KeyError):
        pass
    return

### BUILDING DATABASE ###

# creates class instances and builds database, returns university_list for testing
def create_database():
    university_list = []
    for link in UNIVERSITY_LIST:
        # creating universities
        tuition = get_tuition_data(link)
        acceptance_rate, average_gpa, university_name = get_admissions_data(link)
        lat, lng = get_coordinates_for_university(university_name)
        university = University(university_name, acceptance_rate, tuition, average_gpa, lat, lng)
        university_list.append(university)
        session.add(university)
        major_list = get_academics_data(link)
        # creating majors
        for major_name in major_list:
            major = Major(university_name, major_name)
            session.add(major)
        # creating addresses
        street_address, city, state, zip_code = get_visit_data(link)
        location = Location(university_name, street_address, city, state, zip_code)
        session.add(location)
    session.commit()
    return university_list
   
### DISPLAY FUNCTIONS ###

# takes result set and launches distribution of tuition
def tuition_distrubution(results):
    universities = []
    tuition = []
    # if user requests 'major=', results will be resultset and not just universities
    if type(results[0]) == University:
         universities = results       
    else:
        for result in results:
            universities.append(result[0])
    for university in universities:
        tuition.append(university.tuition)
    fig = go.Figure(data = [go.Histogram(x = tuition)])
    fig.show()
    return

# takes result set and launches map of results
def plot_universities(results):
    universities = []
    # if user requests 'major=', results will be resultset and not just universities
    if type(results[0]) == University:
         universities = results       
    else:
        for result in results:
            universities.append(result[0])
    lat_list = []
    lng_list = []
    name_list = []
    for university in universities:
        lat = university.lat
        lng = university.lng
        if not (lat and lng):
            continue
        else:
            lat_list.append(lat)
            lng_list.append(lng)
            name_list.append(university.name)
    # creates plot
    fig = go.Figure(go.Scattermapbox(
        lat=lat_list,
        lon=lng_list,
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=9
        ),
        text=name_list
    ))
    # adds map to plot
    fig.update_layout(
        hovermode='closest',
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_key,
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=np.mean(lat_list),
                lon=np.mean(lng_list)
            ),
            pitch=0,
            zoom=2.75
        )
    )
    fig.show()
    return
 
# takes result set and launches bar graph of tuition
def graph_tuition(results):
    universities = []
    # if user requests 'major=', results will be resultset and not just universities
    if type(results[0]) == University:
         universities = results       
    else:
        for result in results:
            universities.append(result[0])
    name_list = []
    tuition_list = []
    for university in universities:
        name_list.append(university.name)
        tuition_list.append(university.tuition)
    fig = go.Figure([go.Bar(x=name_list, y=tuition_list)])
    fig.show()

# takes results and displays them in an html table
def display_search_results(command, results):
    gpa = False
    acceptance = False
    is_university = False
    tuition = False
    if type(results[0]) == University:
        is_university = True
        file = open('html.html', 'r')
        contents = file.read()
        file.close()
    else:
        file = open('major_temp.html', 'r')
        contents = file.read()
        file.close()
    if 'acceptance' in command:
        acceptance = True
    if 'gpa' in command:
        gpa = True
    if 'tuition' in command:
        tuition = True
    print('\nLaunching matching results...')
    template = Template(contents)
    html =  template.render(results=results, command=command, tuition=tuition, is_university=is_university, gpa=gpa, acceptance=acceptance)
    f = open('university.html', 'w')
    f.write(html)
    f.close
    webbrowser.open_new('university.html')


### USER INTERFACE ###

# takes validified university search, converts it to a query, and returns query results
def process_university_search(command):
    parameters = command.split()
    major = None
    acceptance = False
    limit = 10
    tuition = None
    state = None
    for parameter in parameters:
        if parameter.startswith('state'):
            state = parameter[6:].upper()
        elif parameter.startswith('major'):
            major = '%' + parameter[6:].replace('_', ' ') + '%'
        elif parameter.startswith('tuition'):
            try:
                tuition = float(parameter[8:])
            except(ValueError):
                return 'Bad command, please try again.'
        elif parameter.startswith('limit'):
            try:
                limit = int(parameter[6:])
            except(ValueError):
                return 'Bad command, please try again.'
        elif parameter in ('search','acceptance','gpa'):
            pass
        else:
            return 'Bad command, please try again.'
    # if major, tuition, and state have been specified
    if major and tuition and state:
        results = session.query(University,func.count(University.name)).join(Location).join(Major).filter(Major.major.like(major)).filter(University.tuition <= tuition).filter(University.tuition>0.0).filter(Location.state == state).group_by(University.name).all()
        return results[0:limit]  
    # if major and tuition are specified
    elif major and tuition and not state:
        results = session.query(University,func.count(University.name)).join(Major).filter(Major.major.like(major)).filter(text(f'University.tuition < {tuition}')).filter(University.tuition>0.0).group_by(Major.name).all()
        return results[0:limit] 
    # if tuition and state are specified
    elif not major and tuition and state:
        results = session.query(University).join(Location).filter(University.tuition <= tuition).filter(University.tuition>0.0).filter(Location.state == state).all()
        return results[0:limit] 
    # if major and state are specified
    elif major and not tuition and state:
        results = session.query(University,func.count(University.name)).join(Location).join(Major).filter(Major.major.like(major)).filter(Location.state == state).group_by(University.name).all()
        return results[0:limit]
    # if major is specified
    elif major and not tuition and not state:
        results = session.query(University,func.count(University.name)).join(Major).filter(Major.major.like(major)).group_by(University.name).all()
        return results[0:limit]
    # if tuition is specified
    elif not major and tuition and not state:
        results = session.query(University).filter(University.tuition <= tuition).filter(University.tuition>0.0)
        return results[0:limit]
    # if state is specified
    elif not major and not tuition and state:
        results = session.query(University).join(Location).filter(Location.state == state).all()
        return results[0:limit]
    else:
        return 'Bad command, please try again.'
    
# takes user command and determines invalid input and which function to pass the command to for results, returns command results
def process_command(command):
    components = command.split()
    results = []
    if len(components) == 0:
        print('Bad command, please try again.')
    elif components[0] == 'search':
        results = process_university_search(command.lower())
    else:
        print('Bad command, please try again.')
    if results == 'Bad command, please try again.':
        print('\n' + results)
    elif len(results) == 0:
        print('\nNo results matched your parameters.')\
    # displays search results in an html table
    elif len(results) > 0:
        display_search_results(command, results)
    return results
    
# setting up database for query use and accomadating for empty caches
empty = False
cwd = os.getcwd()
if not database_exists(f'sqlite:///universities.db'):
    empty = True
if not os.path.exists(os.getcwd() +'\\University_htmls.txt'):
    get_start_sites()
engine = create_engine('sqlite:///universities.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

if __name__ == "__main__":   
    # creates database if non-existent
    if empty:
        print('\nBuilding database...')
        Base.metadata.create_all(engine)
        create_database()
    command = ''
    help = '\nOptions:\n\nEnter \'search\' followed by any combination of these parameters: \'state=\' followed by a state abbreviation, \'major=\' followed by a major with underscores where spaces would be, \'tuition=\' plus a number without commas, decimal points, or other symbols, or \'limit=\' plus a number to limit results by. Add \'gpa\' or \'acceptance\' to this search to have those statistics displayed in results.\n\nOnce you have results, enter \'map\' to map results, \'graph\' to see a bar graph of tuition, or \'distribution\' to see a distribution of tuition.\n\nEnter \'help\' to these options again.\n\nEnter \'quit\' to exit.  '
    results = []
    print('\nEnter a command to get started or enter \'help\' for options and instructions.')
    while command != 'quit':
        command = input('\nEnter prompt: ').lower().strip()
        if command.startswith('search'):
            results = process_command(command)
        elif command.startswith('map'):
            if type(results) == str or len(results) == 0:
                print('\nNo results to map, make a request first.')
            else:
                print('\nLaunching map...')
                plot_universities(results)
        elif command.startswith('graph'):
            if type(results) == str or len(results) == 0:
                print('\nNo results to graph, make a request first.')
            else:
                print('\nLaunching tuition bar graph...')
                graph_tuition(results)
        elif command == 'distribution':
            if type(results) == str or len(results) == 0:
                print('\nNo results to graph, make a request first.')
            else:
                print('\nLaunching tuition distribution...')
                tuition_distrubution(results)
        elif command == 'help':
            print(help)
        elif command == 'rebuild':
            print('\nDeleting tables and rebuilding database...')
            session.query(University).delete()
            session.query(Location).delete()
            session.query(Major).delete()
            session.commit()
            Base.metadata.create_all(engine)
            create_database()
        elif command == 'quit':
            print('\nExiting program...')
        else:
            print('\nInvalid command, please try again.')



# writing cache to file
cache_dump = json.dumps(UNIVERSITIES)
cache_contents = open('university_htmls.txt', 'w')
cache_contents.write(cache_dump)
cache_contents.close()

cache_dump = json.dumps(UNIVERSITY_LIST)
cache_contents = open('links_list.txt', 'w')
cache_contents.write(cache_dump)
cache_contents.close()

cache_dump = json.dumps(GOOGLE_PLACES)
cache_contents = open('google_places.txt', 'w')
cache_contents.write(cache_dump)
cache_contents.close()