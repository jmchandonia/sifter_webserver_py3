from sifter_results_db.models import SifterResults
from term_db.models import Term,Term2Term
from weight_db.models import Weight
from results.models import SIFTER_Output
from django.db import connection
import cPickle,zlib
import pickle
import numpy as np
import math
import os
import datetime
import django
from Bio.Blast import NCBIWWW,NCBIXML

django.setup()

OUTPUT_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"output")

    
def find_go_ancs(ts):
    ancs0=Term.objects.filter(term_id__in=ts).values('ancestors','term_id')
    ancs={}
    for w in ancs0:
        ancs[w['term_id']]=cPickle.loads(zlib.decompress(w['ancestors']).encode('ascii','ignore'))
    return ancs

def find_go_decs(ts):
    decs0=Term.objects.filter(term_id__in=ts).values('descendants','term_id')
    decs={}
    for w in decs0:
        decs[w['term_id']]=cPickle.loads(zlib.decompress(w['descendants']).encode('ascii','ignore'))
    return decs

def find_go_decs_ancs(ts):
    res0=Term.objects.filter(term_id__in=ts).values('ancestors','descendants','term_id')
    ancs={}
    decs={}
    for w in res0:
        decs[w['term_id']]=cPickle.loads(zlib.decompress(w['descendants']).encode('ascii','ignore'))
        ancs[w['term_id']]=cPickle.loads(zlib.decompress(w['ancestors']).encode('ascii','ignore'))        
    return decs,ancs

def find_go_childs(ts):
    res0=Term2Term.objects.filter(parent_id__in=ts).values_list(flat=True)
    childs={}
    for w in res0:
        if w[0] not in childs:
            childs[w[0]]=[]
        childs[w[0]].append(w[1])
    #for w in set(ts)-set(childs.keys()):
    #    childs[w]=set([])        
    return childs

def find_go_parents(ts):
    res0=Term2Term.objects.filter(child_id__in=ts).values_list(flat=True)
    parents={}
    for w in res0:
        if w[1] not in parents:
            parents[w[1]]=[]
        parents[w[1]].append(w[0])
    for w in set(ts)-set(parents.keys()):
        parents[w]=set([])
    return parents
    
def find_eps(ts):
    res0=Term.objects.filter(term_id__in=ts).values('term_id','eps')
    eps={}
    for w in res0:
        eps[w['term_id']]=w['eps']
    return eps
    
def find_weights(fams):
    res0=Weight.objects.filter(pfam__in=fams).values()
    weights={}
    for w in res0:
        fam=w['pfam']
        ww=w['weight']
        code=w['conf_code']
        if fam not in weights:
            weights[fam]={}
        weights[fam][code]=ww
    return weights

def map_scores_goa(res):
    bad_flag=0
    mn=min(res.values())    
    if mn<0:
        res={k:(v-mn) for k,v in res.iteritems()}
        bad_flag=1
    mx=max(res.values())    
    if mx>1:
        res={k:(v/float(mx)) for k,v in res.iteritems()}        
        bad_flag=1
    if bad_flag==1:
        res={k:(v*.3) for k,v in res.iteritems()}        
    terms=res.keys()
    ancs=find_go_ancs(terms)
    terms2=set([v for w in ancs.values() for v in w])|set(terms)
    parents=find_go_parents(terms2)
    childs=find_go_childs(terms2)        
    decs,ancs=find_go_decs_ancs(terms2)
    eps=find_eps(terms2)
    all_anc=set([v for w in ancs.values() for v in w])
    anc_dict={}
    for t,a in ancs.iteritems():
        for t2 in a:
            if t2 not in anc_dict:
                anc_dict[t2]=[]
            anc_dict[t2].append(t)
    
    todo_list=terms
    order_list=[]
    while todo_list:
        t=todo_list.pop(0)
        if t in order_list:
            continue
        if set(todo_list)&(decs[t]):
            todo_list.append(t)
            continue
        order_list.append(t)
        todo_list.extend(parents[t])
    
    for t in order_list:
        if t in res.keys():
            continue
        ch=childs[t]
        known=set(ch)&set(res.keys())
        zerochilds=set(ch)-set(res.keys())
        unknown=set(ch)&set(all_anc)-known
        if unknown:
            print 'error'
        ps=[res[w] for w in known]
        ps.extend([0 for w in zerochilds])
        res[t]=1+(eps[t]-1)*np.prod(1-np.array(ps))
    return {k:v for k,v in res.iteritems()}

def merge_results(results):
    final_res={}
    for res in results:
        w=res[1][0]*res[0] 
        for term,score in res[1][1].iteritems():
            if term not in final_res:
                final_res[term]=0
            final_res[term]+=score*w
    return final_res

def find_res_multidomain(results):
    n_domain=len(results)
    wt=-0.07*np.log(n_domain)+1
    terms_res={}
    for gid,res in results.iteritems():
        for term in res.keys():
            if term not in terms_res:
                terms_res[term]=[]
            terms_res[term].append(res[term])
    final_res={}
    for term,res in terms_res.iteritems():
        final_res[term]=1-np.prod(1-np.array(res))
    final_res={k:v*wt for k,v in final_res.iteritems()}
    return final_res

def filter_results(input_res,real_terms):
    output_res={}
    for gene,res in input_res.iteritems():
        filtered_res={}
        for t,v in res.iteritems():
            if v>=0.005:
                filtered_res[t]=v
            else:
                if (t in real_terms[gene]) and v>=0.003:
                    filtered_res[t]=0.005
        if len(filtered_res.keys())>0:
            output_res[gene]=filtered_res
    return output_res

def find_db_results(method,q_genes={},species=''):
    if method=='by_protein':
        q_results0=[]
        batchs=100
        for i in range(0,int(np.ceil(float(len(q_genes))/float(batchs)))):
            q_results0.extend(SifterResults.objects.filter(uniprot_id__in=q_genes[batchs*i:min(len(q_genes),batchs*(i+1))]))
        print len(q_results0)
    elif method=='by_species':
        q_results0=SifterResults.objects.filter(tax_id=species)
        
    q_results={}    
    for q_res in q_results0:
        gene=q_res.uniprot_id
        if gene not in q_results:
            q_results[gene]=[]
        q_results[gene].append(q_res)
                  
    taxids={}
    unip_accs={}
    for q_gene in q_results:
        taxids[q_gene]=q_results[q_gene][0].tax_id
        unip_accs[q_gene]=q_results[q_gene][0].uniprot_acc
    return q_results,taxids,unip_accs


def find_processed_results(q_results):
    bads_rn=[]
    q_genes=q_results.keys()
    my_res={}
    for q_gene in q_genes:
        my_res[q_gene]={}
        for res in q_results[q_gene]:
            fam=res.pfam
            pos='%s-%s'%(res.start_pos,res.end_pos)
            conf_code=res.conf_code
            if fam not in my_res[q_gene]:
                my_res[q_gene][fam]={}
            if conf_code not in my_res[q_gene][fam]:
                my_res[q_gene][fam][conf_code]={}
            if pos not in my_res[q_gene][fam][conf_code]:
                my_res[q_gene][fam][conf_code][pos]={}
            pred=cPickle.loads(zlib.decompress(res.preds).encode('ascii','ignore'))
            for goid,score in pred.iteritems():
                if (not score is None) and (score>1e-3):
                    my_res[q_gene][fam][conf_code][pos][goid]=score
    
    my_res_all={k:{} for k in my_res.keys()}
    for i,gene in enumerate(q_genes):
        for fam in my_res[gene].keys():
            my_res_all[gene][fam]={}
            for code,rr in my_res[gene][fam].iteritems():
                my_res_all[gene][fam][code]={}
                for pos,res in rr.iteritems():
                    r=my_res[gene][fam][code][pos]
                    if len(r)==0:
                        bads_rn.append([gene,code,pos,''])
                        continue
                    new_r=map_scores_goa(r)
                    if math.isnan(sum(new_r.values())):
                        bads_rn.append([gene,code,pos,new_r])                            
                        continue
                    else:           
                        my_res_all[gene][fam][code][pos]=new_r

    SIFTER_results={}
    bads=[]
    fams=list(set([v for w in my_res_all.values() for v in w]))
    weights_all=find_weights(fams)
    for gene in my_res_all.keys():
        results={}
        for fam in my_res_all[gene].keys():
            for code,rr in my_res_all[gene][fam].iteritems():
                code0=code[0:3]
                for pos,res in rr.iteritems():
                    gid=pos
                    if gid not in results:
                        results[gid]={}
                    if code0 not in results[gid]:
                        results[gid][code0]=[]
                    if fam not in weights_all:
                        bads.append([fam,code,gene,gid])                            
                        results[gid][code0].append([0.7,res,fam])
                        continue
                    if code0 not in weights_all[fam]:
                        bads.append([fam,code,gene,gid])
                        results[gid][code0].append([0.7,res,fam])
                        continue
                    results[gid][code0].append([weights_all[fam][code0],res,fam])
        SIFTER_results[gene]=results
    print 'bads',bads

    SIFTER_results2={}
    for gene in SIFTER_results.keys():
        SIFTER_results2[gene]={}
        for gid in SIFTER_results[gene]:
            SIFTER_results2[gene][gid]={}
            for code0 in SIFTER_results[gene][gid].keys():
                mm=np.argmax([w[0] for w in  SIFTER_results[gene][gid][code0]])
                SIFTER_results2[gene][gid][code0]=SIFTER_results[gene][gid][code0][mm]                                                    

    real_terms={}
    for gene in SIFTER_results2.keys():
        r_terms=set([])
        for gid in SIFTER_results2[gene].keys():
            for code in SIFTER_results2[gene][gid].keys():
                if 'R' in code:            
                    r_terms|=set([w for w in SIFTER_results2[gene][gid][code][1].keys()])
        real_terms[gene]=r_terms
    return my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms


def find_Model1_results(SIFTER_results2,real_terms,we=0.7,wr=0.95,wc=0.55):
    SIFTER_results_merged_MODEL1={}
    for gene in SIFTER_results2.keys():
        SIFTER_results_merged_MODEL1[gene]={}
        for gid in SIFTER_results2[gene]:
            SIFTER_results_merged_MODEL1[gene][gid]={}
            codes=SIFTER_results2[gene][gid].keys()
            R_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'R' in w]
            I_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'I' in w]        
            C_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'C' in w]        
            T_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'T' in w]
            A_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'A' in w]
            B_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'B' in w]        
            L_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'L' in w]        
            results=[]
            if not C_codes:
                if A_codes:
                    i_code='AIT'
                    r_code='ART'
                elif B_codes:
                    i_code='BIT'
                    r_code='BRT'
                elif L_codes:
                    i_code='LIT'
                    r_code='LRT'                
                if i_code not in codes:
                    results.append([wr,SIFTER_results2[gene][gid][r_code]])
                elif (i_code in codes) and (r_code in codes):
                    results.append([(1-we),SIFTER_results2[gene][gid][i_code]])
                    results.append([we,SIFTER_results2[gene][gid][r_code]])
                else:
                    results.append([(1-we),SIFTER_results2[gene][gid][i_code]])
            else:
                if ('ART' not in codes) and ('AIT' not in codes):
                    i_code='AIC'
                    r_code='ARC'                
                    if i_code not in codes:
                        results.append([wr,SIFTER_results2[gene][gid][r_code]])
                    elif (i_code in codes) and (r_code in codes):
                        results.append([(1-we),SIFTER_results2[gene][gid][i_code]])
                        results.append([we,SIFTER_results2[gene][gid][r_code]])
                    else:
                        results.append([(1-we),SIFTER_results2[gene][gid][i_code]])
                else:
                    res_i={}
                    res_r={}
                    if ('AIC' in codes) and ('AIT' in codes):
                        res_i=[1, merge_results([[wc,SIFTER_results2[gene][gid]['AIC']],[(1-wc),SIFTER_results2[gene][gid]['AIT']]]),'']
                    elif ('AIC' in codes):
                        res_i=SIFTER_results2[gene][gid]['AIC']
                    elif ('AIT' in codes):
                        res_i=SIFTER_results2[gene][gid]['AIT']

                    if ('ARC' in codes) and ('ART' in codes):
                        res_r=[1,merge_results([[wc,SIFTER_results2[gene][gid]['ARC']],[(1-wc),SIFTER_results2[gene][gid]['ART']]]),'']
                    elif ('ARC' in codes):
                        res_r=SIFTER_results2[gene][gid]['ARC']
                    elif ('ART' in codes):
                        res_r=SIFTER_results2[gene][gid]['ART']

                    if len(res_i)==0:
                        results.append([wr,res_r])
                    elif len(res_i)>0 and len(res_r)>0:
                        results.append([(1-we),res_i])
                        results.append([we,res_r])
                    else:
                        results.append([(1-we),res_i])

            SIFTER_results_merged_MODEL1[gene][gid]=merge_results(results)


    MODEL1_my_results={}
    for gene,res in SIFTER_results_merged_MODEL1.iteritems():
        MODEL1_my_results[gene]=find_res_multidomain(res)
    MODEL1_my_results_filtered=filter_results(MODEL1_my_results,real_terms)

    return MODEL1_my_results_filtered



def find_Model2_results(SIFTER_results2,real_terms,wc=0.55):
    SIFTER_results_merged_MODEL2={}
    for gene in SIFTER_results2.keys():
        gid_results={}
        for gid in SIFTER_results2[gene]:
            www={}
            codes=SIFTER_results2[gene][gid].keys()
            R_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'R' in w]
            I_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'I' in w]        
            C_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'C' in w]        
            T_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'T' in w]
            A_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'A' in w]
            B_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'B' in w]        
            L_codes=[w for w in SIFTER_results2[gene][gid].keys() if 'L' in w]
            if R_codes:
                results=[]
                if 'ARC' not in codes:
                    if 'ART' in codes:
                        r_code='ART'
                    elif 'BRT' in codes:
                        r_code='BRT'
                    elif 'LRT' in codes:
                        r_code='LRT'                
                    results.append([1,SIFTER_results2[gene][gid][r_code]])
                    www[r_code]=SIFTER_results2[gene][gid][r_code][0]
                else:
                    if ('ART' not in codes):
                        r_code='ARC'                
                        results.append([1,SIFTER_results2[gene][gid][r_code]])
                        www[r_code]=SIFTER_results2[gene][gid][r_code][0]                    
                    else:
                        res_r=[1,merge_results([[wc,SIFTER_results2[gene][gid]['ARC']],[(1-wc),SIFTER_results2[gene][gid]['ART']]]),'']
                        www['ARC']=SIFTER_results2[gene][gid]['ARC'][0]                                        
                        www['ART']=SIFTER_results2[gene][gid]['ART'][0]                                                            
                        results.append([1,res_r])
                if results:
                    gid_results[gid]=merge_results(results)
        if len(gid_results.keys())>0:
            SIFTER_results_merged_MODEL2[gene]=gid_results
            
    MODEL2_my_results={}
    for gene,res in SIFTER_results_merged_MODEL2.iteritems():
        MODEL2_my_results[gene]=find_res_multidomain(res)
    MODEL2_my_results_filtered=filter_results(MODEL2_my_results,real_terms)
    
    return MODEL2_my_results_filtered

def find_top_preds(preds,thr):
    top_preds={}
    all_terms=list(set([v for w in preds.values() for v in w.keys()]))
    decs=find_go_decs(all_terms)
    for g,pred in preds.iteritems():
        terms=pred.keys()
        leaves=[w for w in terms if not(set(decs[w])&(set(terms)-set([w])))]
        tp={w:pred[w] for w in leaves}
        mx=max(tp.values())*thr
        top_preds[g]={w:round(tp[w],2) for w in tp if tp[w]>mx}
        
    return top_preds

def find_top_preds_func(preds,leaves,thr):
    top_preds={}
    for g,pred in preds.iteritems():
        tp={w:pred[w] for w in leaves[g]}
        mx=max(tp.values())*thr
        top_preds[g]={w:tp[w] for w in tp if tp[w]>mx}        
    return top_preds


def trim_results(res):
    res_trimmed={}
    for gene,v in res.iteritems():
        r={}
        for t,s in v.iteritems():
            ss=round(s,2)
            if ss>0:
                r[t]=ss
        if r:
            res_trimmed[gene]=r
    return res_trimmed

def find_leave_preds(preds):
    
    all_terms=set([v for w in preds.values() for v in w])
    decs=find_go_decs(all_terms)
    leaves={}
    for g,pred in preds.iteritems():
        terms=pred.keys()
        leaves[g]=[w for w in terms if not(set(decs[w])&(set(terms)-set([w])))]        
    return leaves
    
        
def find_sifter_preds_byprotein(q_genes,my_form_data):
    sifter_choices=my_form_data['sifter_choices']
    q_results,taxids,unip_accs=find_db_results('by_protein',q_genes=q_genes)
    my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
    if sifter_choices=='EXP-Model':
        res_filtered=find_Model2_results(SIFTER_results2,real_terms)
    else:
        ExpWeight_hidden=my_form_data['ExpWeight_hidden']
        res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
    trimmed_res=trim_results(res_filtered)
    leaves=find_leave_preds(trimmed_res)
    res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
    return res,taxids,unip_accs

def find_sifter_preds_byspecies(species,my_form_data):
    sifter_choices=my_form_data['sifter_choices']
    q_results,taxids,unip_accs=find_db_results('by_species',species=species)
    my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
    if sifter_choices=='EXP-Model':
        res_filtered=find_Model2_results(SIFTER_results2,real_terms)
    else:
        ExpWeight_hidden=my_form_data['ExpWeight_hidden']
        res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
    trimmed_res=trim_results(res_filtered)
    leaves=find_leave_preds(trimmed_res)
    res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
    return res,taxids,unip_accs

def find_sifter_preds_byfunction(species,functions,my_form_data):
    sifter_choices=my_form_data['sifter_choices']
    q_results,taxids,unip_accs=find_db_results('by_species',species=species)
    my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
    if sifter_choices=='EXP-Model':
        res_filtered=find_Model2_results(SIFTER_results2,real_terms)
    else:
        ExpWeight_hidden=my_form_data['ExpWeight_hidden']
        res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
    trimmed_res=trim_results(res_filtered)
    leaves=find_leave_preds(trimmed_res)
    res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}
    top_preds=find_top_preds_func(trimmed_res,leaves,thr=.75)
    decs=set(find_go_decs(functions))
    res_top={}
    for gene in top_preds:
        if set(top_preds[gene].keys())&decs:
            res_top[gene]=res[gene]                
    taxids={k:v for k,v in taxids.iteritems() if k in res_top}
    unip_accs={k:v for k,v in unip_accs.iteritems() if k in res_top}    
    return res_top,taxids,unip_accs

def find_sifter_preds_byfsequence(my_sequences,my_form_data):
   
    status=0
    try:
        qblast_output = NCBIWWW.qblast("blastp", "swissprot", my_sequences,alignments=0,expect=1e-2)
    except:
        status=1
    
    if status==0:
        my_blast_file=os.path.join(OUTPUT_DIR,"%s_output.blast"%job_id)
        save_file = open(my_blast_file, "w")
        save_file.write(qblast_output.read())
        save_file.close()
        qblast_output.close()
        for record in NCBIXML.parse(open(my_blast_file)):
            if record.alignments :
                for aa in record.alignments:
                    sp_id=aa.hit_id.split('sp|')[1].split('|')[0].split('.')[0]            
                print aa.hsps[0].bits, aa.hsps[0].expect,sp_id

def find_results(my_form_data,job_id):
    active_tab=my_form_data['active_tab_hidden']
    input_file=SIFTER_Output.objects.filter(job_id=job_id).values_list('input_file',flat=True)[0]
    data=pickle.load(open(input_file,'r'))
    if active_tab == 'by_protein':
        my_genes=data['proteins']
        res,taxids,unip_accs=find_sifter_preds_byprotein(my_genes,my_form_data)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump([res,taxids,unip_accs],open(outfile,'w'))
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
        return True
    elif active_tab == 'by_species':
        my_species=data['species']
        res,taxids,unip_accs=find_sifter_preds_byspecies(my_species,my_form_data)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump([res,taxids,unip_accs],open(outfile,'w'))
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
        return True
    elif active_tab == 'by_function':
        my_species=data['species']
        my_functions=Term.objects.filter(acc__in=data['functions']).values_list('term_id',flat=True)
        res,taxids,unip_accs=find_sifter_preds_byfunction(my_species,my_functions,my_form_data)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump([res,taxids,unip_accs],open(outfile,'w'))
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
        return True
    elif active_tab == 'by_sequence':
        my_sequences=data['sequences']
        res,taxids,unip_accs=find_sifter_preds_byfsequence(my_sequences,my_form_data)
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump([res,taxids,unip_accs],open(outfile,'w'))
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
        return True


