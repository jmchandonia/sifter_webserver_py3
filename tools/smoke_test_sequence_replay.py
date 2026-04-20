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

from results.models import SIFTER_Output
from sifter_web.scripts import sqlite_query


SAMPLE_BLAST_FILE = os.path.join(REPO_ROOT, 'sifter_web', 'output', '8563541_output.blast')
FASTA_QUERY = '>seq1\nMNNNKSLAAAVATLSNNAQA\n'


def main():
    original_runner = sqlite_query.run_remote_qblast
    original_send_mail = sqlite_query.send_mail
    try:
        sqlite_query.run_remote_qblast = lambda _sequence: open(SAMPLE_BLAST_FILE)
        sqlite_query.send_mail = lambda *args, **kwargs: 1
        client = Client()
        response = client.post(
            '/',
            {
                'active_tab_hidden': 'by_sequence',
                'sifter_choices': 'EXP-Model',
                'ExpWeight_hidden': '0.7',
                'more_options_hidden': '',
                'input_email': '',
                'input_sequence': FASTA_QUERY,
                'input_queries': '',
                'input_species': '',
                'input_function': '',
                'input_function_sp': '',
                'function_selected_hidden': '',
                'sp_selected_hidden': '',
                'spf_selected_hidden': '',
                'error_sp_hidden': '',
            },
            HTTP_HOST='testserver',
        )
        if response.status_code != 302 or not response.get('Location', '').startswith('/results-id='):
            raise AssertionError(f'unexpected sequence submit response: {response.status_code} {response.get("Location", "")}')

        job_id = int(response['Location'].split('=')[1])
        record = SIFTER_Output.objects.get(job_id=job_id)
        if not record.output_file or not os.path.exists(record.output_file):
            raise AssertionError(f'missing output file for sequence job {job_id}')

        with open(record.output_file, 'rb') as handle:
            results = pickle.load(handle)
        if 'result' not in results or not results['result']:
            raise AssertionError('sequence replay produced no results')

        results_page = client.get(response['Location'], HTTP_HOST='testserver')
        if results_page.status_code != 200:
            raise AssertionError(f'results page returned {results_page.status_code}')

        print('OK sequence replay job', job_id, 'result groups', len(results['result']))
    finally:
        sqlite_query.run_remote_qblast = original_runner
        sqlite_query.send_mail = original_send_mail


if __name__ == '__main__':
    main()
