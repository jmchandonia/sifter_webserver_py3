from sifter_results_db.models import SifterResults
from sifter_results_ready_db.models import SifterResults as SifterResultsReady
from term_db.models import Term,Term2Term
from weight_db.models import Weight
from results.models import SIFTER_Output
from idmap_db.models import Idmap
from pfamdb.models import Pfam
from django.db import connection
import cPickle,zlib
import pickle
import numpy as np
import math
import os
import datetime
import django
from Bio.Blast import NCBIWWW,NCBIXML
import operator
from taxid_db.models import Taxid
import time
import grp
import pwd
from django.core.mail import send_mail

django.setup()

OUTPUT_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"output")
INPUT_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"input")

stat_info = os.stat(os.path.dirname(__file__))
uuid = stat_info.st_uid
ggid = stat_info.st_gid

file_user_id = pwd.getpwuid(uuid)[0]
file_group_id = grp.getgrgid(ggid)[0]

    
def find_go_ancs(ts):
    ts=list(ts)
    ancs0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        ancs0.extend(Term.objects.filter(term_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('ancestors','term_id'))    
    ancs={}
    for w in ancs0:
        ancs[w['term_id']]=cPickle.loads(zlib.decompress(w['ancestors']).encode('ascii','ignore'))
    return ancs

def find_go_decs(ts):
    ts=list(ts)
    decs0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        decs0.extend(Term.objects.filter(term_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('descendants','term_id'))    
    decs={}
    for w in decs0:
        decs[w['term_id']]=cPickle.loads(zlib.decompress(w['descendants']).encode('ascii','ignore'))
    return decs

def find_go_decs_ancs(ts):
    ts=list(ts)
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(Term.objects.filter(term_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('ancestors','descendants','term_id'))    
    ancs={}
    decs={}
    for w in res0:
        decs[w['term_id']]=cPickle.loads(zlib.decompress(w['descendants']).encode('ascii','ignore'))
        ancs[w['term_id']]=cPickle.loads(zlib.decompress(w['ancestors']).encode('ascii','ignore'))        
    return decs,ancs

def find_go_childs(ts):
    ts=list(ts)
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(Term2Term.objects.filter(parent_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values_list(flat=True))    
    childs={}
    for w in res0:
        if w[0] not in childs:
            childs[w[0]]=[]
        childs[w[0]].append(w[1])
    #for w in set(ts)-set(childs.keys()):
    #    childs[w]=set([])        
    return childs

def find_go_parents(ts):
    ts=list(ts)
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(Term2Term.objects.filter(child_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values_list(flat=True))    
    parents={}
    for w in res0:
        if w[1] not in parents:
            parents[w[1]]=[]
        parents[w[1]].append(w[0])
    for w in set(ts)-set(parents.keys()):
        parents[w]=set([])
    return parents
    
def find_eps(ts):
    ts=list(ts)
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(Term.objects.filter(term_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('term_id','eps'))    
    eps={}
    for w in res0:
        eps[w['term_id']]=w['eps']
    return eps
    
def find_weights(fams):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(fams))/float(batchs)))):
        res0.extend(Weight.objects.filter(pfam__in=fams[batchs*i:min(len(fams),batchs*(i+1))]).values())
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


def find_db_ready_results(method,q_genes={},mode=1,species=''):
    if method=='by_protein':
        q_results0=[]
        batchs=100
        for i in range(0,int(np.ceil(float(len(q_genes))/float(batchs)))):
            q_results0.extend(SifterResultsReady.objects.filter(uniprot_id__in=q_genes[batchs*i:min(len(q_genes),batchs*(i+1))],mode=mode))
        
   
        q_results={}    
        taxids={}
        unip_accs={}
        for q_res in q_results0:
            q_gene=q_res.uniprot_id
            q_results[q_gene]=cPickle.loads(zlib.decompress(q_res.preds).encode('ascii','ignore'))
            taxids[q_gene]=q_res.tax_id
            unip_accs[q_gene]=q_res.uniprot_acc
    
        
    elif method=='by_species':
        q_results0=SifterResultsReady.objects.filter(tax_id=species,mode=mode).values('uniprot_id','preds','tax_id','uniprot_acc')
    
        q_results={}    
        taxids={}
        unip_accs={}
        for q_res in q_results0:
            q_gene=q_res['uniprot_id']
            q_results[q_gene]=cPickle.loads(zlib.decompress(q_res['preds']).encode('ascii','ignore'))
            taxids[q_gene]=q_res['tax_id']
            unip_accs[q_gene]=q_res['uniprot_acc']
    

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
    if bads:
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


def find_Model1_results(SIFTER_results2,real_terms,we=0.7,wr=0.95,wc=0.55,return_domiand_preds=False):
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

    if not return_domiand_preds:
        MODEL1_my_results={}
        for gene,res in SIFTER_results_merged_MODEL1.iteritems():
            MODEL1_my_results[gene]=find_res_multidomain(res)
        MODEL1_my_results_filtered=filter_results(MODEL1_my_results,real_terms)

        return MODEL1_my_results_filtered
    else:
        SIFTER_results_merged_MODEL1_filtered={}
        for gene,res in SIFTER_results_merged_MODEL1.iteritems():
            SIFTER_results_merged_MODEL1_filtered[gene]=filter_results(SIFTER_results_merged_MODEL1[gene],real_terms)

        return SIFTER_results_merged_MODEL1_filtered

def find_Model2_results(SIFTER_results2,real_terms,wc=0.55,return_domiand_preds=False):
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
 
    if not return_domiand_preds:
        MODEL2_my_results={}
        for gene,res in SIFTER_results_merged_MODEL2.iteritems():
            MODEL2_my_results[gene]=find_res_multidomain(res)
        MODEL2_my_results_filtered=filter_results(MODEL2_my_results,real_terms)

        return MODEL2_my_results_filtered
    else:
        SIFTER_results_merged_MODEL2_filtered={}
        for gene,res in SIFTER_results_merged_MODEL2.iteritems():
            SIFTER_results_merged_MODEL2_filtered[gene]=filter_results(SIFTER_results_merged_MODEL2[gene],real_terms)

        return SIFTER_results_merged_MODEL2_filtered
           
    

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

def find_top_preds_func(preds,thr):
    top_preds={}
    for g,pred in preds.iteritems():
        mx=max(pred.values())*thr
        top_preds[g]={w:pred[w] for w in pred if pred[w]>mx}        
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
    
        
def find_sifter_preds_byprotein(q_genes,my_form_data,job_id):
    
    acc_ids=Idmap.objects.filter(other_id__in=q_genes, db='ID').values_list('unip_id','other_id')
    accs_ids_maps={w[1]:w[0] for w in acc_ids}
    q_genes=[accs_ids_maps[w] if w in accs_ids_maps else w for w in q_genes]
    data={'proteins':q_genes}
    infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
    pickle.dump(data,open(infile,'w'))
    os.system("chmod 775 %s"%infile)
    os.system('chown %s %s'%(file_user_id,infile))
    os.system('chgrp %s %s'%(file_group_id,infile))
    sifter_choices=my_form_data['sifter_choices']
    ExpWeight_hidden=float(my_form_data['ExpWeight_hidden'])
    if ((sifter_choices=='EXP-Model') or ((sifter_choices=='ALL-Model')and(ExpWeight_hidden==0.7))):
        if sifter_choices=='EXP-Model':
            mode=1
        else:
            mode=0
        q_results,taxids,unip_accs=find_db_ready_results('by_protein',q_genes=q_genes,mode=mode)
        return q_results,taxids,unip_accs
    else:        
        q_results,taxids,unip_accs=find_db_results('by_protein',q_genes=q_genes)
        my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
        if sifter_choices=='EXP-Model':
            res_filtered=find_Model2_results(SIFTER_results2,real_terms)
        else:
            res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
        trimmed_res=trim_results(res_filtered)
        leaves=find_leave_preds(trimmed_res)
        res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
        return res,taxids,unip_accs

def find_sifter_preds_byspecies(species,my_form_data):
    sifter_choices=my_form_data['sifter_choices']
    ExpWeight_hidden=float(my_form_data['ExpWeight_hidden'])
    if ((sifter_choices=='EXP-Model') or ((sifter_choices=='ALL-Model')and(ExpWeight_hidden==0.7))):
        if sifter_choices=='EXP-Model':
            mode=1
        else:
            mode=0
        q_results,taxids,unip_accs=find_db_ready_results('by_species',mode=mode,species=species)
        return q_results,taxids,unip_accs
    else:        
        q_results,taxids,unip_accs=find_db_results('by_species',species=species)
        my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
        if sifter_choices=='EXP-Model':
            res_filtered=find_Model2_results(SIFTER_results2,real_terms)
        else:
            res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
        trimmed_res=trim_results(res_filtered)
        leaves=find_leave_preds(trimmed_res)
        res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
        return res,taxids,unip_accs

def find_sifter_preds_byfunction(species,functions,my_form_data):
    sifter_choices=my_form_data['sifter_choices']
    ExpWeight_hidden=float(my_form_data['ExpWeight_hidden'])
    if ((sifter_choices=='EXP-Model') or ((sifter_choices=='ALL-Model')and(ExpWeight_hidden==0.7))):
        if sifter_choices=='EXP-Model':
            mode=1
        else:
            mode=0
        res,taxids,unip_accs=find_db_ready_results('by_species',mode=mode,species=species)
    else:
        q_results,taxids,unip_accs=find_db_results('by_species',species=species)
        my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
        if sifter_choices=='EXP-Model':
            res_filtered=find_Model2_results(SIFTER_results2,real_terms)
        else:
            res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
        trimmed_res=trim_results(res_filtered)
        leaves=find_leave_preds(trimmed_res)
        res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}
    
    top_preds=find_top_preds_func(res,thr=.75)
    decs=set(find_go_decs(functions))
    res_top={}
    for gene in top_preds:
        if set(top_preds[gene].keys())&decs:
            res_top[gene]=res[gene]                
    taxids={k:v for k,v in taxids.iteritems() if k in res_top}
    unip_accs={k:v for k,v in unip_accs.iteritems() if k in res_top}    
    return res_top,taxids,unip_accs

def find_sifter_preds_bysequence(my_sequences,my_form_data,job_id):
   
    blast_hits={}
    connected=0
    cnt=0
    while connected==0:
        try:
            qblast_output = NCBIWWW.qblast("blastp", "nr", my_sequences,alignments=0,expect=1e-2,hitlist_size=100,ncbi_gi=True)            
            connected=1
            my_blast_msg_file=os.path.join(OUTPUT_DIR,"%s_output.blast.msg"%job_id)
            save_file = open(my_blast_msg_file, "w")
            save_file.write("We have successful submitted your query to NCBI-BLAST server. Results will be ready soon.")
            save_file.close()            
        except:
            if cnt<600:
                if np.mod(cnt,60)==0:
                    print("NCBI-BLAST Server has been busy for the last %s mins. We keep trying to connect."%(cnt))
                my_blast_msg_file=os.path.join(OUTPUT_DIR,"%s_output.blast.msg"%job_id)
                save_file = open(my_blast_msg_file, "w")
                save_file.write("NCBI-BLAST Server has been busy for the last %s mins. We keep trying to connect."%(cnt))
                save_file.close()            
                time.sleep(60)
            else:
                break
            cnt+=1

    if connected==0:
        return 0,0,0,0,0 #"BLAST Server was busy for last 10 hours; please try again later"
    else:
        my_blast_file=os.path.join(OUTPUT_DIR,"%s_output.blast"%job_id)
        save_file = open(my_blast_file, "w")
        save_file.write(qblast_output.read())
        save_file.close()
        qblast_output.close()
        os.system("chmod 775 %s"%my_blast_file)
        os.system('chown %s %s'%(file_user_id,my_blast_file))
        os.system('chgrp %s %s'%(file_group_id,my_blast_file))
        gis=[]
        hits={}
        for record in NCBIXML.parse(open(my_blast_file)):
            if record.alignments :
                hits[record.query]=[]
                for aa in record.alignments:
                    gi=aa.hit_id.split('gi|')
                    if len(gi)>0:
                        gi_num=gi[1].split('|')[0]
                        gis.append(gi_num)
                        hit_id={'P_GI':gi_num}
                    else:
                        hit_id={'all':aa.hit_id}
                    hits[record.query].append({'hit_id':hit_id,'bits':aa.hsps[0].bits,'eval':aa.hsps[0].expect,
                                               'ident':round(aa.hsps[0].identities/float(aa.hsps[0].align_length)*100),
                                               'Q_cov':round(abs(float(aa.hsps[0].query_end-aa.hsps[0].query_start))/record.query_length*100)
                                               })
        mapped_gis=Idmap.objects.filter(other_id__in=gis, db='GI').values_list('other_id','unip_id')
        mapped_gis={w[0]:w[1] for w in mapped_gis}
        #mapped_gis=uni.map(gis, f='P_GI', t='ID') # map single id
        #mapped_gis={k:list(v)[0] for k,v in mapped_gis.iteritems() if v}
        q_genes=[]
        for record in hits:
            blast_hits[record]=[]
            for hit in hits[record]:
                if hit['hit_id'].keys()[0]=='P_GI':
                    gi=hit['hit_id']['P_GI']
                    if gi in mapped_gis:
                        if mapped_gis[gi] not in q_genes:
                            blast_hits[record].append([mapped_gis[gi],hit['bits'],hit['eval'],hit['ident'],hit['Q_cov']])
                            q_genes.append(mapped_gis[gi])

        sifter_choices=my_form_data['sifter_choices']
        ExpWeight_hidden=float(my_form_data['ExpWeight_hidden'])
        if ((sifter_choices=='EXP-Model') or ((sifter_choices=='ALL-Model')and(ExpWeight_hidden==0.7))):
            if sifter_choices=='EXP-Model':
                mode=1
            else:
                mode=0
            q_results,taxids,unip_accs=find_db_ready_results('by_protein',q_genes=q_genes,mode=mode)
            return q_results,taxids,unip_accs,blast_hits,1
        else:        
            q_results,taxids,unip_accs=find_db_results('by_protein',q_genes=q_genes)
            my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
            if sifter_choices=='EXP-Model':
                res_filtered=find_Model2_results(SIFTER_results2,real_terms)
            else:
                res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden)
            trimmed_res=trim_results(res_filtered)
            leaves=find_leave_preds(trimmed_res)
            res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
            return res,taxids,unip_accs,blast_hits,1

    
def find_go_name_acc(ts):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(Term.objects.filter(term_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('term_id','name','acc'))
    idx_to_go_name={}
    for w in res0:
        idx_to_go_name[w['term_id']]=[w['acc'],w['name']]
    return idx_to_go_name


def find_name_taxids(ts):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(Taxid.objects.filter(tax_id__in=ts[batchs*i:min(len(ts),batchs*(i+1))]).values('tax_id','tax_name'))
    taxid_2_name={}
    for w in res0:
        taxid_2_name[w['tax_id']]=w['tax_name']
    for w in set(ts)-set(taxid_2_name.keys()):
        taxid_2_name[w]=w
    return taxid_2_name

def make_results_ready(job_id,activ_tab,my_data):
    results={}
    if not activ_tab=='by_sequence':
        res,taxids,unip_accs=my_data
        terms=list(set([v for w in res.values() for v in w]))
        idx_to_go_name=find_go_name_acc(terms)
        taxid_2_name=find_name_taxids(list(set(taxids.values())))
        result=[]
        for j,gene in enumerate(res):
            preds=[]            
            res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
            tax_name=taxid_2_name[taxids[gene]]
            if len(res_sorted)<=3:
                end_i=len(res)
            else:
                end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[2][1]*.75)]
                if end_i:
                   end_i=end_i[-1]
                else:
                   end_i=1
   
            for i, pred  in enumerate(res_sorted):
                term,score=pred
                if i<=end_i:                    
                    preds.append([idx_to_go_name[term][0],idx_to_go_name[term][1],str(score)])
                else:
                    break
            result.append([gene,unip_accs[gene],tax_name,taxids[gene],preds])
        print result
        result=sorted(result,key=lambda x:float(x[4][0][2]),reverse=True)
        if activ_tab == 'by_protein':
            infile=os.path.join(INPUT_DIR,"%s_input.pickle"%job_id)
            data=pickle.load(open(infile))
            my_genes=data['proteins']
            rest=list(set(my_genes)-set(res.keys()))
            if rest:
                nopred_file=os.path.join(OUTPUT_DIR,"%s_nopreds.txt"%job_id)
                nopred_file_o=open(nopred_file,'w')
                nopred_file_o.write('List of genes with no predictions: \n'+'\n'.join(rest))
                nopred_file_o.close()
                os.system('chmod 775 %s'%nopred_file)
                os.system('chown %s %s'%(file_user_id,nopred_file))
                os.system('chgrp %s %s'%(file_group_id,nopred_file))
                results['nopreds']=[nopred_file,len(rest)]
                
                
        output_download_file=os.path.join(OUTPUT_DIR,"%s_download.txt"%job_id)
        output_download_file_o=open(output_download_file,'w')
        output_download_file_o.write('SIFTER Predictions for Job ID %s: \n\n'%job_id)        
        for r in result:
            output_download_file_o.write('Uniprot ID: %s\n'%r[0])        
            output_download_file_o.write('Species: %s\n'%r[2])
            output_download_file_o.write('Predictions:\tGO ID\tTerm name\tConfidence Score\n')
            for pred in r[4]:
                output_download_file_o.write('\t\t%s\t%s\t%s\n'%(pred[0],pred[1],pred[2]))        
            output_download_file_o.write('\n')                                    
        output_download_file_o.close()
        os.system("chmod 775 %s"%output_download_file)
        os.system('chown %s %s'%(file_user_id,output_download_file))
        os.system('chgrp %s %s'%(file_group_id,output_download_file))        
        results['downloadfile']=output_download_file
    else:
        res,taxids,unip_accs,blast_hits,connected=my_data        
        terms=list(set([v for w in res.values() for v in w]))
        idx_to_go_name=find_go_name_acc(terms)
        taxid_2_name=find_name_taxids(list(set(taxids.values())))
        result=[]
        for query, hits in blast_hits.iteritems():
            result_q=[]
            for j,hit in enumerate(hits):
                preds=[]
                gene=hit[0]
                if gene not in res:
                    continue
                res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
                tax_name=taxid_2_name[taxids[gene]]
                if len(res_sorted)<=3:
                    end_i=len(res)
                else:
                    end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[2][1]*.75)]
                    if end_i:
                       end_i=end_i[-1]
                    else:
                       end_i=1
    
                for i, pred  in enumerate(res_sorted):
                    term,score=pred
                    if i<=end_i:                    
                        preds.append([idx_to_go_name[term][0],idx_to_go_name[term][1],str(score)])
                    else:
                        break
                result_q.append([gene,unip_accs[gene],tax_name,taxids[gene],'%d'%hit[1],'%.2e'%hit[2],'%0.0f'%hit[3],'%0.0f'%hit[4],preds])
            result.append([query,result_q])
        output_download_file=os.path.join(OUTPUT_DIR,"%s_download.txt"%job_id)
        output_download_file_o=open(output_download_file,'w')
        output_download_file_o.write('SIFTER Predictions for Job ID %s: \n\n'%job_id)        
        for q in result:
            output_download_file_o.write('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')        
            output_download_file_o.write('Predictions for homologs of the query sequence: %s\n'%q[0])        
            output_download_file_o.write('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')        
            for r in q[1]:
                output_download_file_o.write('Uniprot ID: %s\n'%r[0])        
                output_download_file_o.write('Species: %s\n'%r[2])
                output_download_file_o.write('BLAST Hit Information: (Bit-Score: %s, E-val:%s, Identitiy:%s, Query Coverage:%s\n'%(r[4],r[5],r[6],r[7]))
                output_download_file_o.write('Predictions:\tGO ID\tTerm name\tConfidence Score\n')
                for pred in r[8]:
                    output_download_file_o.write('\t\t%s\t%s\t%s\n'%(pred[0],pred[1],pred[2]))        
                output_download_file_o.write('\n')                                    
            output_download_file_o.write('\n')                                    

        output_download_file_o.close()
        os.system("chmod 775 %s"%output_download_file)
        os.system('chown %s %s'%(file_user_id,output_download_file))
        os.system('chgrp %s %s'%(file_group_id,output_download_file))
        results['downloadfile']=output_download_file
            
    results['result']=result
    return results

        
                        
def find_results(my_form_data,job_id):
    active_tab=my_form_data['active_tab_hidden']
    input_file=SIFTER_Output.objects.filter(job_id=job_id).values_list('input_file',flat=True)[0]
    data=pickle.load(open(input_file,'r'))
    if active_tab == 'by_protein':
        my_genes=data['proteins']
        res,taxids,unip_accs=find_sifter_preds_byprotein(my_genes,my_form_data,job_id)
        results=make_results_ready(job_id,active_tab,[res,taxids,unip_accs])
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump(results,open(outfile,'w'))
        os.system("chmod 775 %s"%outfile)
        os.system('chown %s %s'%(file_user_id,outfile))
        os.system('chgrp %s %s'%(file_group_id,outfile))
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
    elif active_tab == 'by_species':
        my_species=data['species']
        res,taxids,unip_accs=find_sifter_preds_byspecies(my_species,my_form_data)
        results=make_results_ready(job_id,active_tab,[res,taxids,unip_accs])        
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump(results,open(outfile,'w'))
        os.system("chmod 775 %s"%outfile)
        os.system('chown %s %s'%(file_user_id,outfile))
        os.system('chgrp %s %s'%(file_group_id,outfile))        
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
    elif active_tab == 'by_function':
        my_species=data['species']
        my_functions=Term.objects.filter(acc__in=data['functions']).values_list('term_id',flat=True)
        res,taxids,unip_accs=find_sifter_preds_byfunction(my_species,my_functions,my_form_data)
        results=make_results_ready(job_id,active_tab,[res,taxids,unip_accs])        
        outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
        pickle.dump(results,open(outfile,'w'))
        os.system("chmod 775 %s"%outfile)
        os.system('chown %s %s'%(file_user_id,outfile))
        os.system('chgrp %s %s'%(file_group_id,outfile))        
        my_object=SIFTER_Output.objects.filter(job_id=job_id)
        my_object=my_object[0]        
        my_object.result_date=datetime.date.today()        
        my_object.output_file=outfile
        my_object.save()
    elif active_tab == 'by_sequence':
        my_sequences=data['sequences']
        res,taxids,unip_accs,blast_hits,connected=find_sifter_preds_bysequence(my_sequences,my_form_data,job_id)
        if not connected==0:
            results=make_results_ready(job_id,active_tab,[res,taxids,unip_accs,blast_hits,connected])        
            outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
            pickle.dump(results,open(outfile,'w'))
            os.system("chmod 775 %s"%outfile)
            os.system('chown %s %s'%(file_user_id,outfile))
            os.system('chgrp %s %s'%(file_group_id,outfile))       
            my_object=SIFTER_Output.objects.filter(job_id=job_id)
            my_object=my_object[0]        
            my_object.result_date=datetime.date.today()        
            my_object.output_file=outfile
            my_object.save()
        else:
            outfile=os.path.join(OUTPUT_DIR,"%s_output.pickle"%job_id)
            results={}
            results['bad_blast']=True
            pickle.dump(results,open(outfile,'w'))
            os.system("chmod 775 %s"%outfile)
            os.system('chown %s %s'%(file_user_id,outfile))
            os.system('chgrp %s %s'%(file_group_id,outfile))       
            my_object=SIFTER_Output.objects.filter(job_id=job_id)
            my_object=my_object[0]        
            my_object.result_date=datetime.date.today()        
            my_object.output_file=outfile
            my_object.save()    
    my_object=SIFTER_Output.objects.filter(job_id=job_id)[0]
    msg='results in: http://sifter.berkeley.edu/results-id=%s\n'%job_id
    msg+='Job submitted on: %s\n'%my_object.submission_date
    msg+='Results ready on: %s\n'%my_object.result_date
    msg+='query_method: %s\n'%my_object.query_method
    msg+='SIFTER choice: %s\n'%my_object.sifter_EXP_choices
    msg+='EXP Weight: %s\n'%my_object.exp_weight
    msg+='Number of proteins: %s\n'%my_object.n_proteins
    msg+='Species: %s\n'%my_object.species
    msg+='Number of functions: %s\n'%my_object.n_functions
    msg+='Number of sequences: %s\n'%my_object.n_sequences
    send_mail('SIFTER-WEB run for Job ID:%s'%job_id, msg, 'sifter@compbio.berkeley.edu',['sahraeian.m@gmail.com'], fail_silently=False)
    return True





def find_results_domain(q_gene,sifter_EXP_choices,ExpWeight_hidden):
    q_results,taxids,unip_accs=find_db_results('by_protein',q_genes=[q_gene])
    my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
    gid_to_fam={k:v.values()[0][2].split('_')[0] for k,v in SIFTER_results2[q_gene].iteritems()}
    real_terms={k:real_terms[q_gene] for k in gid_to_fam.keys()}
    fam_to_name={}
    fams=Pfam.objects.filter(pfam_acc__in=set(gid_to_fam.values())).values('pfam_acc','pfam_id')
    for w in fams:
        fam_to_name[w['pfam_acc']]=w['pfam_id']
    found_fams=fam_to_name.keys()
    for w in set(gid_to_fam.values())-set(found_fams):
        fam_to_name[w]=''

    if sifter_EXP_choices:
        res_filtered=find_Model2_results(SIFTER_results2,real_terms,return_domiand_preds=True)
    else:
        res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight_hidden,return_domiand_preds=True)
    trimmed_res=trim_results(res_filtered[q_gene])
    leaves=find_leave_preds(trimmed_res)
    res={gid:{k:v for k,v in pred.iteritems() if k in leaves[gid]} for gid,pred in trimmed_res.iteritems()}
    terms=list(set([v for w in res.values() for v in w]))
    idx_to_go_name=find_go_name_acc(terms)
    result=[]
    for j,gid in enumerate(res):
        preds=[]
        res_sorted=sorted(res[gid].iteritems(),key=operator.itemgetter(1),reverse=True)
        if len(res_sorted)<=3:
            end_i=len(res)
        else:
            end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[2][1]*.75)]
            if end_i:
               end_i=end_i[-1]
            else:
               end_i=1

        for i, pred  in enumerate(res_sorted):
            term,score=pred
            if i<=end_i:                    
                preds.append([idx_to_go_name[term][0],idx_to_go_name[term][1],str(score)])
            else:
                break
        fam=gid_to_fam[gid]
        if fam[0:2]=='PF':
            link="family/%s"%fam
        elif fam[0:2]=='PB':
            link="pfamb/%s"%fam
                
        result.append([gid,fam,fam_to_name[fam],link,preds])            
        result=sorted(result, key=lambda x: int(x[0].split('-')[0]))
    return result,unip_accs[q_gene]
