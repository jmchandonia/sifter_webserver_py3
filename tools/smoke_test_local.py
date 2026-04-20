import os
import pickle
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, REPO_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sifter_web.settings_dev')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver')

import django

django.setup()

from django.test import Client


def assert_status(client, path, status, location_prefix=None):
    response = client.get(path, HTTP_HOST='testserver')
    if response.status_code != status:
        raise AssertionError(f"{path}: expected {status}, got {response.status_code}")
    if location_prefix and not response.get('Location', '').startswith(location_prefix):
        raise AssertionError(
            f"{path}: expected redirect starting with {location_prefix}, got {response.get('Location', '')}"
        )
    print(f"OK {path} -> {response.status_code} {response.get('Location', '')}")
    return response


def assert_form_redirect(client, payload):
    response = client.post('/', payload, HTTP_HOST='testserver')
    if response.status_code != 302 or not response.get('Location', '').startswith('/results-id='):
        raise AssertionError(f"POST / expected results redirect, got {response.status_code} {response.get('Location', '')}")
    print(f"OK POST / -> {response.status_code} {response['Location']}")
    return response['Location']


def main():
    client = Client()

    for path in ['/', '/about/', '/help/', '/download/', '/complexity/']:
        assert_status(client, path, 200)

    assert_status(client, '/search/?q=654924', 302, '/predictions/?taxid=')
    assert_status(client, '/search/?q=GO:0047128', 302, '/predictions/?term=')
    assert_status(client, '/search/?q=001R_FRG3G', 302, '/predictions/?protein=')
    assert_status(client, '/search/autocomplete?dbs=taxid&q=654924', 200)
    assert_status(client, '/search/autocomplete?dbs=term&q=GO:0047128', 200)
    assert_status(client, '/search/autocomplete?dbs=unip&q=001R_FRG3G', 200)
    assert_status(client, '/search_options/?q=654924', 302, '/predictions/?s-taxid=')
    assert_status(client, '/results-id=9999789', 200)

    protein_redirect = assert_status(client, '/predictions/?protein=001R_FRG3G', 302, '/results-id=')
    species_redirect = assert_status(client, '/predictions/?taxid=654924', 302, '/results-id=')
    assert_status(client, protein_redirect['Location'], 200)
    assert_status(client, species_redirect['Location'], 200)

    function_redirect = assert_form_redirect(
        client,
        {
            'active_tab_hidden': 'by_function',
            'function_selected_hidden': 'GO:0047128',
            'spf_selected_hidden': '654924',
            'ExpWeight_hidden': '0.7',
            'sifter_choices': 'EXP-Model',
            'more_options_hidden': '',
            'input_email': '',
            'input_function': '',
            'input_function_sp': '',
            'input_queries': '',
            'input_species': '',
            'input_sequence': '',
            'sp_selected_hidden': '',
            'error_sp_hidden': '',
        },
    )
    assert_status(client, function_redirect, 200)

    with open(os.path.join(REPO_ROOT, 'sifter_web', 'output', '3882317_output.pickle'), 'rb') as handle:
        protein = pickle.load(handle)['result'][0][0]
    assert_status(client, f'/results-id=3882317/protein={protein}', 200)


if __name__ == '__main__':
    main()
