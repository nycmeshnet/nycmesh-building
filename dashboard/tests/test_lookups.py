from django.test import Client, TestCase
from bs4 import BeautifulSoup

class TestLookups(TestCase):

    def test_name(self):
        form_data = {
            'query': 'alice'
        }

        response = self.client.post("/", form_data)

        #print(response.content)

        self.assertEqual(response.status_code, 200)

        self.assertIn('<select name="selected_member" class="form-select" id="selected_member">', response.content.decode())
        self.assertContains(response, '<option value="1018">Alice</option>', html=True)

        soup = BeautifulSoup(response.content.decode())
        select = soup.find('select')
        member_id = select.findChildren()[0]['value']

        form_data = {
            'selected_member': member_id
        }

        response = self.client.post("/", form_data)
        
        soup = BeautifulSoup(response.content.decode())
        tables = soup.find_all('table')

        self.assertEquals(len(tables), 3)