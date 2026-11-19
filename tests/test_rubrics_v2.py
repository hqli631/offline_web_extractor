from copy import deepcopy
import unittest

from src.webextractor.rubrics_v2 import score

def doc(*blocks, title='1. Example'):
    return {'title':title, 'blocks':list(blocks)}

def block(text, kind='paragraph', **attrs):
    return {'kind':kind,'text':text,**attrs}

class RubricsV2Tests(unittest.TestCase):
    def setUp(self):
        self.gold=doc(block('Alpha paragraph'),block('Second paragraph'),block('Subheading','heading',heading_level=2))

    def test_exact_and_no_applicable_code(self):
        result=score(self.gold,self.gold)
        self.assertEqual(result['decision'],'pass')
        self.assertFalse(result['needs_human_review'])
        self.assertEqual(result['dimensions']['format']['status'],'not_applicable')
        self.assertIsNone(result['overall'])

    def test_missing_gold_is_unknown_not_perfect(self):
        result=score(self.gold)
        self.assertEqual(result['decision'],'uncertain')
        self.assertTrue(all(d['score'] is None for d in result['dimensions'].values()))

    def test_text_replacement_limits_coverage_not_structure_attribute_quality(self):
        pred=deepcopy(self.gold)
        pred['blocks'][0]['text']='Changed paragraph'
        result=score(pred,self.gold)
        self.assertLess(result['dimensions']['completeness']['recall'],1)
        structure=result['dimensions']['structure']
        self.assertEqual(structure['attribute_ratio'],1)
        self.assertEqual(structure['status'],'partial')
        self.assertLess(structure['alignment_coverage'],1)
        self.assertEqual(result['decision'],'uncertain')

    def test_reordering_same_kind_blocks_detected(self):
        pred=deepcopy(self.gold)
        pred['blocks'][0],pred['blocks'][1]=pred['blocks'][1],pred['blocks'][0]
        result=score(pred,self.gold)
        self.assertEqual(result['dimensions']['completeness']['recall'],1)
        self.assertLess(result['dimensions']['structure']['order_ratio'],1)
        self.assertEqual(result['decision'],'fail')

    def test_heading_and_list_attributes_separate_from_text(self):
        for attrs in ({'heading_level':3},{'kind':'paragraph'}):
            pred=deepcopy(self.gold)
            pred['blocks'][2].update(attrs)
            result=score(pred,self.gold)
            self.assertEqual(result['dimensions']['completeness']['recall'],1)
            self.assertEqual(result['decision'],'fail')
            issue=next(x for x in result['issues'] if x['code']=='attribute_mismatch')
            self.assertEqual(issue['predicted_ref'],'p:2')
            self.assertEqual(issue['gold_ref'],'g:2')
        gold=doc(block('Item','list_item',list_type='ol',ordinal=1,depth=0))
        pred=deepcopy(gold); pred['blocks'][0]['depth']=1
        self.assertEqual(score(pred,gold)['decision'],'fail')

    def test_dom_id_does_not_change_structure_but_footnote_label_does(self):
        gold=doc(block('Footnote','footnote',footnote_label='[1]',source_id='id2'))
        pred=deepcopy(gold);pred['blocks'][0]['source_id']='new-id'
        self.assertEqual(score(pred,gold)['decision'],'pass')
        pred['blocks'][0]['footnote_label']='[2]'
        self.assertEqual(score(pred,gold)['decision'],'fail')

    def test_code_whitespace_is_format_not_structure(self):
        gold=doc(block('if ok:\n    run()\n','code'))
        pred=doc(block('if ok:\nrun()\n','code'))
        result=score(pred,gold)
        self.assertEqual(result['dimensions']['structure']['score'],4)
        self.assertEqual(result['dimensions']['format']['score'],0)
        self.assertEqual(result['decision'],'fail')

    def test_duplicate_blocks_cannot_inflate_recall(self):
        gold=doc(block('Repeated'))
        pred=doc(block('Repeated'),block('Repeated'))
        result=score(pred,gold)
        self.assertEqual(result['dimensions']['completeness']['recall'],1)
        self.assertLess(result['dimensions']['cleanliness']['precision'],1)
        self.assertEqual(result['dimensions']['structure']['status'],'partial')
        self.assertTrue(any(x['predicted_ref']=='p:1' for x in result['issues']))

    def test_prompt_looking_text_is_data_and_terms_are_casefolded(self):
        gold=doc(block('Ignore previous instructions ADVERTISEMENT'))
        self.assertEqual(score(gold,gold,noise_terms=['advertisement','ADVERTISEMENT'])['decision'],'pass')
        pred=deepcopy(gold); pred['blocks'].append(block('ADVERTISEMENT'))
        result=score(pred,gold,noise_terms=['advertisement','ADVERTISEMENT'])
        self.assertEqual(result['dimensions']['cleanliness']['noise_hits'],{'advertisement':1})

    def test_title_number_error_and_partial_evidence(self):
        pred=deepcopy(self.gold);pred['title']='Example'
        result=score(pred,self.gold)
        self.assertEqual(result['dimensions']['title']['score'],3)
        self.assertTrue(result['needs_human_review'])
        partial=score(self.gold,self.gold,evidence_complete=False)
        self.assertEqual(partial['decision'],'uncertain')
        self.assertTrue(all(d['status']=='partial' for d in partial['dimensions'].values() if d['score'] is not None))

    def test_empty_and_invalid_inputs(self):
        self.assertEqual(score(doc(),self.gold)['decision'],'fail')
        for pred in ({},{'blocks':'bad'},{'blocks':[{'kind':'paragraph','text':None}]}):
            with self.assertRaises(ValueError): score(pred,self.gold)

    def test_no_alignment_is_not_zero_or_perfect_structure(self):
        result=score(doc(block('Entirely different')),self.gold)
        self.assertIsNone(result['dimensions']['structure']['score'])
        self.assertEqual(result['dimensions']['structure']['status'],'unscored')
        self.assertEqual(result['decision'],'fail')

    def test_absent_title_annotation_and_empty_reference_do_not_hide_gaps(self):
        without_title={'blocks':self.gold['blocks']}
        self.assertIsNone(score(self.gold,without_title)['dimensions']['title']['score'])
        result=score(self.gold,doc())
        self.assertEqual(result['dimensions']['completeness']['recall'],1)
        self.assertEqual(result['dimensions']['cleanliness']['precision'],0)
        self.assertEqual(result['decision'],'fail')

if __name__=='__main__': unittest.main()
