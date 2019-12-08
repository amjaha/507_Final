from final_project import *
import unittest
import os
import sqlite3


class Test(unittest.TestCase):
      
    def test_process_command(self):
        #bad command
        results = process_command('adhoasj=ajsd')
        length = len(results)
        self.assertEqual(length, 0)
        #empty command
        results = process_command('')
        length = len(results)
        self.assertEqual(length, 0)
        #search with 0 results
        results = process_command('search state=NY tuition=100')
        length = len(results)
        self.assertEqual(length, 0)
        #search with results
        results = process_command('search state=NY')
        length = len(results)
        self.assertEqual(length, 10)
        #search with results and limit
        results = process_command('search state=NY limit=15')
        length = len(results)
        self.assertEqual(length, 15)

   
    def test_process_university_search(self):       
        #state and tuition and major
        results = process_university_search('search state=NY tuition=50000 major=computer_science')
        university = results[0][0]        
        majors = results[0][1]
        engine = create_engine('sqlite:///universities.db', echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        count = session.query(University.name).join(Major).filter(Major.major.like('%computer science%')).filter(University.name == university.name).all()
        self.assertEqual(university.location[0].state,'NY')
        self.assertTrue(university.tuition <= 50000)
        self.assertEqual(len(count), majors)
        #state and tuition
        results = process_university_search('search state=NY tuition=20000')
        university = results[1]
        self.assertEqual(university.location[0].state,'NY')
        self.assertTrue(university.tuition <= 20000)
        #tuition
        results = process_university_search('search tuition=20000')
        university = results[1]
        self.assertTrue(university.tuition <= 20000)
        #state
        results = process_university_search('search state=NY')
        university = results[1]
        self.assertTrue(university.location[0].state == 'NY')
    
    def test_universities_data(self):
        harvard_link = 'https://www.princetonreview.com/college/harvard-college-1022984'
        state_link = 'https://www.princetonreview.com/college/michigan-state-university-1022671'
        #get_coordinates_for_unviserity
        lat, lng = get_coordinates_for_university('Michigan State University')
        self.assertTrue(abs(lat - 42.701848) < 0.001)
        self.assertTrue(abs(lng - (-84.4821719)) < 0.001)
        lat, lng = get_coordinates_for_university('Harvard College')
        self.assertTrue(abs(lat - 42.3770029) < 0.001)
        self.assertTrue(abs(lng - (-71.1166601)) < 0.001)
        #get_visit_data
        street_address, city, state, zip_code = get_visit_data(harvard_link)
        self.assertEqual(street_address, '86 Brattle Street')
        self.assertEqual(state, 'MA')
        self.assertEqual(city, 'Cambridge')
        self.assertEqual(zip_code, '02138')
        street_address, city, state, zip_code = get_visit_data(state_link)
        self.assertEqual(street_address, '250 Administration Building')
        self.assertEqual(state, 'MI')
        self.assertEqual(city, 'East Lansing')
        self.assertEqual(zip_code, '48824')
        #get_tuition_data
        tuition = get_tuition_data(harvard_link)
        self.assertEqual(tuition, 46340)
        tuition = get_tuition_data(state_link)
        self.assertEqual(tuition, 16650)
        #get_academics_data
        major_list = get_academics_data(harvard_link)
        self.assertEqual(type(major_list), list)
        major_list = get_academics_data(state_link)
        self.assertEqual(type(major_list), list)
        #get_admissions_data
        acceptance_rate, average_gpa, university_name = get_admissions_data(harvard_link)
        self.assertEqual(acceptance_rate, 5.0)
        self.assertEqual(average_gpa, '4.18')
        self.assertEqual(university_name, 'Harvard College')
        acceptance_rate, average_gpa, university_name = get_admissions_data(state_link)
        self.assertEqual(acceptance_rate, 78.0)
        self.assertEqual(average_gpa, '3.73')
        self.assertEqual(university_name, 'Michigan State University')
  
    def test_create_universities(self):
        #call function
        engine = create_engine('sqlite:///universities.db', echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.query(University).delete()
        session.query(Location).delete()
        session.query(Major).delete()
        session.commit()
        Base.metadata.create_all(engine)
        create_database()
        #test tables   
        count = session.query(func.count(Major.major)).all()[0][0]
        print(count)
        self.assertTrue(count > 0)
        count = session.query(func.count(University.name)).all()[0][0]
        self.assertTrue(count > 0)
        count = session.query(func.count(Location.name)).all()[0][0]
        self.assertTrue(count> 0)

    def test_scraping(self):
        #call for one page
        pages = get_start_sites(1)
        #check for link from first page in pages
        self.assertTrue("https://www.princetonreview.com/college/harvard-college-1022984#!visiting" in pages)
        pages = get_start_sites(3)
        #check for link from second and third page in pages
        self.assertTrue('https://www.princetonreview.com/college/university-michigan--ann-arbor-1023092#!visiting' in pages)
        self.assertTrue('https://www.princetonreview.com/college/university-maryland--college-park-1022953#!visiting' in pages)
    
unittest.main()
