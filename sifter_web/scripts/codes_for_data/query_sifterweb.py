#!/usr/bin/python
import cPickle,zlib
import numpy as np
import math
from Bio.Blast import NCBIWWW,NCBIXML
import operator
import time
import sqlite3
import getopt
import sys
import re
def usage():
    print "\nUsage: query_sifterweb.py [options] <q_type> <output_file>\n"
    print "Examples:"
    print "			query_sifterweb.py -p PA24B_MOUSE by_p output.txt\n"
    print "			query_sifterweb.py -p RISC_MOUSE,PADI2_RAT -e ALL by_p output.txt\n"
    print "			query_sifterweb.py -p Q920A5 -e ALL -w 0.9 by_p output.txt\n"
    print "			query_sifterweb.py -i input.txt by_p output.txt\n"
    print "			query_sifterweb.py -s 882 by_s output.txt\n"
    print "			query_sifterweb.py -s 882 -e ALL by_s output.txt\n"
    print "			query_sifterweb.py -f GO:0004657 -s 882 by_f output.txt\n"
    print "			query_sifterweb.py -i input.fasta by_seq output.txt\n"
    print "This function queries SIFTER webserver data to find protein function"
    print "predictions using SIFTER algorithm."
    print "You can submit you jobs to SIFTER web server too at: sifter.berkeley.edu."
    print "The algorithm presented in the following paper:"
    print "- Engelhardt BE, Jordan MI, Srouji JR, Brenner SE. 2011. Genome-scale"
    print "phylogenetic function annotation of large and diverse protein families."
    print "Genome Research 21:1969-1980. \n"
    print "inputs:"
    print "		<query_type>	The querying approach. It can be one"
    print "				of the following terms"
    print "				\"by_p\": to predict by protein ID. Input should be"
    print " 						entered using -p or -i options."
    print "				\"by_s\": to predict for all proteins of a species."
    print "						Input should be entered using -s option."
    print "				\"by_f\": to find proteins that have given functions."
    print "						Input functions should be entered using -f"
    print "						or -i options. The species to llok in"
    print "						should also be entered using -s option."
    print "				\"by_seq\": to predict for homologs of given"
    print "						sequences. Input sequences should be"
    print "						entered using -i option in th Fasta format."
    print "		<output_file>	Path to the output file where the results"
    print "				will be written to." 
    print "options: "
    print "				-p	STRING	list of query protein(s) (use Uniprot ID"
    print "						or Accession, with comma seperation)."
    print "				-s	STRING	NCBI taxonomy ID for input species."
    print "				-f	STRING	list of query function(s)"
    print "						(use GO term IDs)."
    print "				-i	STRING	Path to the input file where the search"
    print "						terms are placed."
    print "				-e 	STRING	Evidence handling scheme:"
    print "						(EXP: using experimental evidence only,"
    print "						ALL: using all experimental and"
    print "						non-experimental evidence.) [Default: EXP]"
    print "				-w	FLOAT	weight to balance experimental and"
    print "						non-experimental evidence when ALL is"
    print "						selected for evidence handling. The"
    print "						entered number (between 0-1) indicates"
    print "						experimental weight [Default: 0.7]"
    print "				-h		Help. Print Usage."

def PRINT_STR(inStr):

    sys.stdout.write(inStr)
    sys.stdout.flush()

term_db_file = 'term_db.sqlite3'
weight_db_file ='weight_db.sqlite3'
taxid_db_file ='taxid_db_wP.sqlite3'
idmap_db_file='idmap_db.sqlite3'
sifter_res_db_file='sifter_results_cmp_wREST.sqlite3'
sifter_res_ready_db_file='sifter_results_cmp_ready_leaves_wREST.sqlite3'

def get_sq_results(db_file,table,selects,q_field,val):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    q_mark=','.join(['?']*len(val))
    wheres=[]
    vals=[]
    for i,q in enumerate(q_field):
        q_mark=','.join(['?']*len(val[i]))
        vals.extend(val[i])
        wheres.append('%s in (%s)'%(q,q_mark))
    wheres=' and '.join(wheres)
    c.execute("select %s from %s where %s"%(selects,table,wheres), vals)
    
    result = c.fetchall()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()
    #return cPickle.loads(result[0].encode('ascii','ignore'))
    return result

def find_go_ancs(ts):
    ts=list(ts)
    ancs0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        ancs00=get_sq_results(term_db_file,'term','term_id,ancestors',['term_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]])
        ancs0.extend(ancs00)        
    ancs={}
    for w in ancs0:
        ancs[w[0]]=cPickle.loads(zlib.decompress(w[1]).encode('ascii','ignore'))
    return ancs

def find_go_decs(ts):
    ts=list(ts)
    decs0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        decs00=get_sq_results(term_db_file,'term','term_id,descendants',['term_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]])
        decs0.extend(decs00)        
    decs={}
    for w in decs0:
        decs[w[0]]=cPickle.loads(zlib.decompress(w[1]).encode('ascii','ignore'))
    return decs

def find_go_decs_ancs(ts):
    ts=list(ts)
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res00=get_sq_results(term_db_file,'term','term_id,descendants,ancestors',['term_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]])
        res0.extend(res00)        
    ancs={}
    decs={}
    for w in res0:
        decs[w[0]]=cPickle.loads(zlib.decompress(w[1]).encode('ascii','ignore'))
        ancs[w[0]]=cPickle.loads(zlib.decompress(w[2]).encode('ascii','ignore'))        
    return decs,ancs

def find_go_childs(ts):
    ts=list(ts)
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res00=get_sq_results(term_db_file,'term2term','parent_id,child_id',['parent_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]])
        res0.extend(res00)        
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
        res00=get_sq_results(term_db_file,'term2term','parent_id,child_id',['child_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]])
        res0.extend(res00)        
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
        res00=get_sq_results(term_db_file,'term','term_id,eps',['term_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]])
        res0.extend(res00)        
    eps={}
    for w in res0:
        eps[w[0]]=w[1]
    return eps
    
def find_weights(fams):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(fams))/float(batchs)))):
        res00=get_sq_results(weight_db_file,'weight','pfam,weight,conf_code',['pfam'],[fams[batchs*i:min(len(fams),batchs*(i+1))]])
        res0.extend(res00)    
    weights={}
    for w in res0:
        fam=w[0]
        ww=w[1]
        code=w[2]
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
    if method=='by_p':
        q_results0=[]
        batchs=100
        for i in range(0,int(np.ceil(float(len(q_genes))/float(batchs)))):
            res0=get_sq_results(sifter_res_db_file,'sifter_results','uniprot_id,uniprot_acc,tax_id,start_pos,end_pos,pfam,nterms,tree_size,conf_code,preds',['uniprot_id'],[q_genes[batchs*i:min(len(q_genes),batchs*(i+1))]])
            q_results0.extend(res0)
    elif method=='by_s':
        q_results0=get_sq_results(sifter_res_db_file,'sifter_results','uniprot_id,uniprot_acc,tax_id,start_pos,end_pos,pfam,nterms,tree_size,conf_code,preds',['tax_id'],[[species]])
        
    q_results={}    
    for q_res in q_results0:
        gene=q_res[0]
        if gene not in q_results:
            q_results[gene]=[]
        q_results[gene].append(q_res)
                  
    taxids={}
    unip_accs={}
    for q_gene in q_results:
        taxids[q_gene]=q_results[q_gene][0][2]
        unip_accs[q_gene]=q_results[q_gene][0][1]
    return q_results,taxids,unip_accs


def find_db_ready_results(method,q_genes={},mode=1,species=''):
    if method=='by_p':
        q_results0=[]
        batchs=100
        for i in range(0,int(np.ceil(float(len(q_genes))/float(batchs)))):
            res0=get_sq_results(sifter_res_ready_db_file,'sifter_results','uniprot_id,uniprot_acc,tax_id,mode,preds',['uniprot_id','mode'],[q_genes[batchs*i:min(len(q_genes),batchs*(i+1))],[mode]])
            q_results0.extend(res0)        
   
        q_results={}    
        taxids={}
        unip_accs={}
        for q_res in q_results0:
            q_gene=q_res[0]
            q_results[q_gene]=cPickle.loads(zlib.decompress(q_res[4]).encode('ascii','ignore'))
            taxids[q_gene]=q_res[2]
            unip_accs[q_gene]=q_res[1]
    
        
    elif method=='by_s':
        q_results0=get_sq_results(sifter_res_ready_db_file,'sifter_results','uniprot_id,uniprot_acc,tax_id,mode,preds',['tax_id','mode'],[[species],[mode]])
           
        q_results={}    
        taxids={}
        unip_accs={}
        for q_res in q_results0:
            q_gene=q_res[0]
            q_results[q_gene]=cPickle.loads(zlib.decompress(q_res[4]).encode('ascii','ignore'))
            taxids[q_gene]=q_res[2]
            unip_accs[q_gene]=q_res[1]
    

    return q_results,taxids,unip_accs


def find_processed_results(q_results):
    bads_rn=[]
    q_genes=q_results.keys()
    my_res={}
    for q_gene in q_genes:
        my_res[q_gene]={}
        for res in q_results[q_gene]:
            fam=res[5]
            pos='%s-%s'%(res[3],res[4])
            conf_code=res[8]
            if fam not in my_res[q_gene]:
                my_res[q_gene][fam]={}
            if conf_code not in my_res[q_gene][fam]:
                my_res[q_gene][fam][conf_code]={}
            if pos not in my_res[q_gene][fam][conf_code]:
                my_res[q_gene][fam][conf_code][pos]={}
            pred=cPickle.loads(zlib.decompress(res[9]).encode('ascii','ignore'))
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
    ''''if bads:
        print 'bads',bads'''

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
    
        
def find_sifter_preds_byprotein(q_genes):
    acc_ids=get_sq_results(idmap_db_file,'idmap','unip_id,other_id',['other_id','db'],[q_genes,['ID']])
    accs_ids_maps={w[1]:w[0] for w in acc_ids}
    q_genes=[accs_ids_maps[w] if w in accs_ids_maps else w for w in q_genes]
    if ((scheme=='EXP') or ((scheme=='ALL')and(ExpWeight==0.7))):
        if scheme=='EXP':
            mode=1
        else:
            mode=0
        q_results,taxids,unip_accs=find_db_ready_results('by_p',q_genes=q_genes,mode=mode)
        return q_results,taxids,unip_accs
    else:        
        q_results,taxids,unip_accs=find_db_results('by_p',q_genes=q_genes)
        my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
        if scheme=='EXP':
            res_filtered=find_Model2_results(SIFTER_results2,real_terms)
        else:
            res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight)
        trimmed_res=trim_results(res_filtered)
        leaves=find_leave_preds(trimmed_res)
        res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
        return res,taxids,unip_accs

def find_sifter_preds_byspecies(species):
    if ((scheme=='EXP') or ((scheme=='ALL')and(ExpWeight==0.7))):
        if scheme=='EXP':
            mode=1
        else:
            mode=0
        q_results,taxids,unip_accs=find_db_ready_results('by_s',mode=mode,species=species)
        return q_results,taxids,unip_accs
    else:        
        q_results,taxids,unip_accs=find_db_results('by_s',species=species)
        my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
        if scheme=='EXP':
            res_filtered=find_Model2_results(SIFTER_results2,real_terms)
        else:
            res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight)
        trimmed_res=trim_results(res_filtered)
        leaves=find_leave_preds(trimmed_res)
        res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
        return res,taxids,unip_accs

def find_sifter_preds_byfunction(species,functions):
    if ((scheme=='EXP') or ((scheme=='ALL')and(ExpWeight==0.7))):
        if scheme=='EXP':
            mode=1
        else:
            mode=0
        res,taxids,unip_accs=find_db_ready_results('by_s',mode=mode,species=species)
    else:
        q_results,taxids,unip_accs=find_db_results('by_s',species=species)
        my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
        if scheme=='EXP':
            res_filtered=find_Model2_results(SIFTER_results2,real_terms)
        else:
            res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight)
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

def find_sifter_preds_bysequence(my_sequences,output_file):
   
    blast_hits={}
    connected=0
    cnt=0
    while connected==0:
        try:
            print "Connecting to BLAST Server."
            qblast_output = NCBIWWW.qblast("blastp", "nr", my_sequences,alignments=0,expect=1e-2,hitlist_size=100,ncbi_gi=True)
            connected=1
        except:
            cnt+=1
            if cnt<60:
                print "BLAST Server is busy, will sleep and try again in 1 minute."
                time.sleep(60)
    if connected==0:
        print "BLAST Server was busy for last hour; please try again later."		
        usage()
        sys.exit()
    else:
        my_blast_file=output_file+".blast"
        save_file = open(my_blast_file, "w")
        save_file.write(qblast_output.read())
        save_file.close()
        qblast_output.close()
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
        mapped_gis=get_sq_results(idmap_db_file,'idmap','other_id,unip_id',['other_id','db'],[gis,['GI']])
        
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

        if ((scheme=='EXP') or ((scheme=='ALL')and(ExpWeight==0.7))):
            if scheme=='EXP':
                mode=1
            else:
                mode=0
            q_results,taxids,unip_accs=find_db_ready_results('by_p',q_genes=q_genes,mode=mode)
            return q_results,taxids,unip_accs,blast_hits,1
        else:        
            q_results,taxids,unip_accs=find_db_results('by_p',q_genes=q_genes)
            my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
            if scheme=='EXP':
                res_filtered=find_Model2_results(SIFTER_results2,real_terms)
            else:
                res_filtered=find_Model1_results(SIFTER_results2,real_terms,we=ExpWeight)
            trimmed_res=trim_results(res_filtered)
            leaves=find_leave_preds(trimmed_res)
            res={gene:{k:v for k,v in pred.iteritems() if k in leaves[gene]} for gene,pred in trimmed_res.iteritems()}    
            return res,taxids,unip_accs,blast_hits,1

    
def find_go_name_acc(ts):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(get_sq_results(term_db_file,'term','term_id,name,acc',['term_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]]))    
    idx_to_go_name={}
    for w in res0:
        idx_to_go_name[w[0]]=[w[2],w[1]]
    return idx_to_go_name


def find_name_taxids(ts):
    res0=[]
    batchs=100
    for i in range(0,int(np.ceil(float(len(ts))/float(batchs)))):
        res0.extend(get_sq_results(taxid_db_file,'taxid','tax_id,tax_name',['tax_id'],[ts[batchs*i:min(len(ts),batchs*(i+1))]]))    
    taxid_2_name={}
    for w in res0:
        taxid_2_name[w[0]]=w[1]
    for w in set(ts)-set(taxid_2_name.keys()):
        taxid_2_name[w]=w
    return taxid_2_name

def make_results_ready(q_type,output_file,my_data):
    results={}
    if not q_type=='by_seq':
        res,taxids,unip_accs=my_data
        terms=list(set([v for w in res.values() for v in w]))
        idx_to_go_name=find_go_name_acc(terms)
        taxid_2_name=find_name_taxids(list(set(taxids.values())))
        result=[]
        for j,gene in enumerate(res):
            preds=[]            
            res_sorted=sorted(res[gene].iteritems(),key=operator.itemgetter(1),reverse=True)
            tax_name=taxid_2_name[taxids[gene]]
            if len(res_sorted)<=2:
                end_i=len(res)
            else:
                end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[1][1]*.75)]
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
                
                
        output_file_o=open(output_file,'w')
        output_file_o.write('SIFTER Predictions: \n\n')        
        for r in result:
            output_file_o.write('Uniprot ID: %s\n'%r[0])        
            output_file_o.write('Species: %s\n'%r[2])
            output_file_o.write('Predictions:\tGO ID\tTerm name\tConfidence Score\n')
            for pred in r[4]:
                output_file_o.write('\t\t%s\t%s\t%s\n'%(pred[0],pred[1],pred[2]))        
            output_file_o.write('\n')                                    
        output_file_o.close()                
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
                if len(res_sorted)<=2:
                    end_i=len(res)
                else:
                    end_i=[i for  i, pred  in enumerate(res_sorted) if pred[1]>(res_sorted[1][1]*.75)]
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
        output_file_o=open(output_file,'w')
        output_file_o.write('SIFTER Predictions: \n\n')        
        for q in result:
            output_file_o.write('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')        
            output_file_o.write('Predictions for homologs of the query sequence: %s\n'%q[0])        
            output_file_o.write('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')        
            for r in q[1]:
                output_file_o.write('Uniprot ID: %s\n'%r[0])        
                output_file_o.write('Species: %s\n'%r[2])
                output_file_o.write('BLAST Hit Information: (Bit-Score: %s, E-val:%s, Identitiy:%s, Query Coverage:%s\n'%(r[4],r[5],r[6],r[7]))
                output_file_o.write('Predictions:\tGO ID\tTerm name\tConfidence Score\n')
                for pred in r[8]:
                    output_file_o.write('\t\t%s\t%s\t%s\n'%(pred[0],pred[1],pred[2]))        
                output_file_o.write('\n')                                    
            output_file_o.write('\n')                                    

        output_file_o.close()                
    

    
if __name__=="__main__":
    
    # Initialization
    #Default parameters
    scheme= "EXP"
    ExpWeight=0.7
    input_file=''
    proteins=[]
    functions=[]
    TaxID=''
    my_sequences=''
    # Check for options
    opts, args = getopt.getopt(sys.argv[1:], "hp:s:f:i:e:w:") 
    if len(args) != 2:
        usage()
        sys.exit()
    if len(opts)>0:
        for o, a in opts:
            if o == "-e":
                scheme = a
            elif o == "-w":
                ExpWeight = float(a)
            elif o == "-i":
                input_file = a
            elif o == "-p":
                splited =re.split(' |,|;\n',a.strip())
                proteins=list(set([w for w in splited if w]))
            elif o == "-s":
                TaxID = a
            elif o == "-f":
                splited =re.split(' |,|;\n',a.strip())
                functions=list(set([w for w in splited if w]))
            else:
                usage()
                sys.exit()
    
    q_type=args[0]
    output_file=args[1]
    
    if q_type == 'by_p':
        print "Job: Predict by protein ID!"
        if input_file and not proteins:
            f = open(input_file, 'r')
            a=f.read()
            splited =re.split(' |,|;\n',a.strip())
            proteins=list(set([w for w in splited if w]))
        if proteins:
            res,taxids,unip_accs=find_sifter_preds_byprotein(proteins)
            make_results_ready(q_type,output_file,[res,taxids,unip_accs])
        else:
            print "ERROR: Please provide list of input protein(s)"
            usage()
            sys.exit()
    elif q_type == 'by_s':
        print "Job: Predict for all proteins of a species!"
        if TaxID:
            res,taxids,unip_accs=find_sifter_preds_byspecies(TaxID)
            make_results_ready(q_type,output_file,[res,taxids,unip_accs])
        else:
            print "ERROR: Please provide NCBI Taxonomy ID for your query speices"
            usage()
            sys.exit()
    elif q_type == 'by_f':
        print "Job: Find proteins that have given function(s)!"
        if input_file and not functions:
            f = open(input_file, 'r')
            a=f.read()
            splited =re.split(' |,|;\n',a.strip())
            functions=list(set([w for w in splited if w]))
        if not TaxID:
            print "ERROR: Please provide NCBI Taxonomy ID for your query speices"
            usage()
            sys.exit()
        if functions:
            my_functions=get_sq_results(term_db_file,'term','term_id',['acc'],[functions])
            my_functions=[w[0] for w in my_functions]
            res,taxids,unip_accs=find_sifter_preds_byfunction(TaxID,my_functions)
            make_results_ready(q_type,output_file,[res,taxids,unip_accs])
        else:
            print "ERROR: Please provide list of input function(s)"
            usage()
            sys.exit()
    elif q_type == 'by_seq':
        print "Job: Predict for homologs of given sequnce(s)!"
        if input_file:
            f = open(input_file, 'r')
            my_sequences=f.read()
        if not my_sequences:
            print "ERROR: Please provide your query sequence(s)"
            usage()
            sys.exit()
        res,taxids,unip_accs,blast_hits,connected=find_sifter_preds_bysequence(my_sequences,output_file)
        make_results_ready(q_type,output_file,[res,taxids,unip_accs,blast_hits,connected])        
    else:
        print "ERROR: Wrong query type."
        usage()
        sys.exit()
    print "DONE!"
   
  
