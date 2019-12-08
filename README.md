# 507_Final
Data:
The data used in this program is basic information about American universities, from the Princeton Review website. The following link goes to the page where I started scraping: https://www.princetonreview.com/college-search. From there, data was recovered from individual university pages. I used the Google Maps API to get the latitude and longitude for each university for mapping. A Google API key will be needed for this portion of the application.
 
Core functions:
This project has 3 major sections. One scrapes the data, another builds the database, and the last  one handles user interaction.  I take command line input and pass it to the appropriate subprocessing function, typically process_command(). This deconstructs the user request converts it to a query, collects the necessary data, and returns it as a list. get_start_sites() is used to begin the scraping process, collecting data for all universities on a given number of pages, set inside this function.  Create_university_items() constructs class objects for University, Major, and Location and constructs the database from cached data. The University class hold name, acceptance, tuition, gpa, latitude and longitude. Major take university name and the major itself, and address holds university name, street address, zip code, city, and state. 

Operating instructions:
To search universities, enter 'search' followed by any combination of these parameters: 'state=' followed by a state abbreviation; 'major=' followed by a major with underscores where spaces would be; 'tuition=' plus a number without commas, decimal points, or other symbols; 'limit=' plus a number to limit results by (default is 10). Add 'gpa' or 'acceptance' to this search to have those statistics displayed in results.
Enter 'Best University in the World' to see the best university in the world.
Once you have results, enter 'map' to map results or 'graph' to see a bar graph of tuition or distribution to see a distribution of tuition.
Enter 'help' display options.
Enter 'quit' to exit.
Enter ‘rebuild’ to reconstruct the database

