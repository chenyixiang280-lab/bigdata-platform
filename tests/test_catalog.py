"""Synthetic-only regression tests for lookup, provenance and update boundaries."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from catalog import Catalog, bind, digest, difference, member_path
from package_catalog import package


def fixture(path, *, native='id-a', field='amount', status='HISTORICAL_AVAILABLE', code='SELECT 1;', wrong_hash=False):
    sha=hashlib.sha256(code.encode()).hexdigest()
    row={'fqn':'demo.sales','native_id':native,'detail':{'tableDesc':'销售'},
         'schema':{'fieldsInfos':[{'name':field,'type':'decimal','comment':'销售额'}],
                   'partitions':[{'name':'dt','type':'string'}]},'heat':{'hotValue':None}}
    record={'fqn':'demo.sales','native_id':native,'lineage':{'status':'OBSERVED_EMPTY','upstream':[],'downstream':[]},
            'assets':{'source_status':status},'description':{'status':'NOT_CAPTURED'}}
    entry={'fqn':row['fqn'],'native_id':native,'record':'tables/a.json','sql_source_status':status,
           'description_status':'NOT_CAPTURED','description':None,
           'sources':[{'path':'offline_sources/a.sql','sha256':'bad' if wrong_hash else sha,'version':1}]}
    with ZipFile(path,'w') as z:
        for name,value in [('snapshot/snapshot.json',{'tables':[row]}),('provenance/index.json',{'summary':{},'tables':[entry]}),('provenance/tables/a.json',record)]:
            z.writestr(name,json.dumps(value,ensure_ascii=False))
        z.writestr('provenance/offline_sources/a.sql',code)
        z.writestr('provenance/audit/private.json','{"cookie":"must-not-be-distributed"}')
        z.writestr('browser_profile/secret.txt','must-not-be-distributed')
    return path


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.archive=fixture(self.root/'a.zip')

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_lookup_fields_and_empty_lineage(self):
        with Catalog(self.archive) as c:
            self.assertEqual(c.table('demo.sales')['schema']['partitions'][0]['name'],'dt')
            self.assertEqual(c.search('销售额',fields=True)['matches_total'],1)
            self.assertEqual(c.record('demo.sales')['lineage']['status'],'OBSERVED_EMPTY')
            self.assertEqual(c.text('demo.sales','sql')['status'],'HISTORICAL_AVAILABLE')
            with self.assertRaises(ValueError):c.table('wrong.sales')

    def test_integrity_and_no_execution(self):
        archive=fixture(self.root/'inert.zip',code='DROP TABLE demo.sales;')
        with Catalog(archive) as c:
            self.assertEqual(c.text('demo.sales','sql')['text'],'DROP TABLE demo.sales;')
            self.assertEqual(c.validate()['tables'],1)
        with self.assertRaisesRegex(ValueError,'HASH_CHANGED'):Catalog(self.archive,'0'*64)
        bad=fixture(self.root/'bad.zip',wrong_hash=True)
        with Catalog(bad) as c:
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):c.validate()

    def test_bind_update_preserves_history_and_reports_structure(self):
        binding=self.root/'state/catalog.json'
        bind(self.archive,digest(self.archive),binding)
        updated=fixture(self.root/'b.zip',field='net_amount')
        result=bind(updated,digest(updated),binding)
        self.assertEqual(result['changes']['changed'][0]['components'],['schema'])
        self.assertTrue((binding.parent/'history'/f'{digest(self.archive)}.json').is_file())
        self.assertEqual(json.loads(binding.read_text())['sha256'],digest(updated))

    def test_identity_change_does_not_change_binding(self):
        binding=self.root/'catalog.json'
        bind(self.archive,digest(self.archive),binding)
        before=binding.read_bytes()
        changed=fixture(self.root/'other.zip',native='new-id')
        with self.assertRaisesRegex(ValueError,'IDENTITY_CHANGED'):
            bind(changed,digest(changed),binding)
        self.assertEqual(before,binding.read_bytes())

    def test_scope_difference_does_not_call_absence_physical_deletion(self):
        other=self.root/'different-scope.zip'
        with ZipFile(self.archive) as src, ZipFile(other,'w') as out:
            for name in src.namelist():
                content=src.read(name)
                if name.endswith('.json') and name!='provenance/audit/private.json':
                    content=content.replace(b'demo.sales',b'demo.other').replace(b'id-a',b'id-b')
                out.writestr(name,content)
        with Catalog(self.archive) as old, Catalog(other) as new:
            result=difference(old,new)
            self.assertEqual(result['added'],['demo.other'])
            self.assertEqual(result['absent_from_new_scope'],['demo.sales'])
            self.assertNotIn('deleted',result)

    def test_distribution_excludes_unselected_sensitive_artifacts(self):
        output=self.root/'distribution.zip'
        result=package(self.archive,output,self.root/'manifest.json')
        with ZipFile(output) as z:
            self.assertNotIn('browser_profile/secret.txt',z.namelist())
            self.assertNotIn('provenance/audit/private.json',z.namelist())
        self.assertEqual(result['distribution_validation'],'PASS')
        with self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS'):
            package(self.archive,output,self.root/'manifest.json')

    def test_selected_secret_is_rejected(self):
        bad=fixture(self.root/'sensitive.zip',code="password='synthetic-not-a-secret'")
        with self.assertRaisesRegex(ValueError,'SENSITIVE_TEXT'):
            package(bad,self.root/'rejected.zip',self.root/'rejected.json')
        self.assertFalse((self.root/'rejected.json').exists())

    def test_reference_paths_and_tampered_record_are_rejected(self):
        with self.assertRaises(ValueError):member_path('../outside.sql')
        with self.assertRaises(ValueError):member_path('/outside.sql')
        p=self.root/'wrong-record.zip'
        with ZipFile(self.archive) as src, ZipFile(p,'w') as out:
            for name in src.namelist():
                data=src.read(name)
                if name=='provenance/tables/a.json':
                    value=json.loads(data);value['native_id']='wrong';data=json.dumps(value).encode()
                out.writestr(name,data)
        with Catalog(p) as c:
            with self.assertRaisesRegex(ValueError,'RECORD_IDENTITY'):c.validate()


if __name__=='__main__':
    unittest.main()
