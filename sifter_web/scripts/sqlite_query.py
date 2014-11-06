def find_results(form):
    active_tab=form.cleaned_data['active_tab_hidden']
    if active_tab=='by_protein':
        return "HHHHHiiiii"
    
    
    
import _mysql as mysql
import _mysql_exceptions as mysql_exceptions
import MySQLdb.cursors
import csv
import numpy as np
import pickle
import os
import operator
import sqlite3
import cPickle
import zlib

params_brenner = {'db_address': 'ultra.berkeley.edu',
'db_username': 'root',
'db_password': '',
'db_name': 'sifter_db_2'
}
db_brenner = MySQLdb.connect(host=params_brenner['db_address'],
                   user=params_brenner['db_username'],
                   passwd=params_brenner['db_password'],
                   db=params_brenner['db_name'],
                   cursorclass=MySQLdb.cursors.DictCursor)

def msql(query, db=db_brenner):
    c = db.cursor()
    c.execute(query)
    results = c.fetchall()
    c.close()
    return results

# In[4]:

evidence_constraints_exp = {
    # Experimental
    'EXP': 0.9,  # Experiment
    'IDA': 0.9,  # Direct Assay
    'IPI': 0.8,  # Physical Interaction
    'IMP': 0.8,  # Mutant Phenotype
    'IGI': 0.8,  # Genetic Interaction
    'IEP': 0.4,  # Expression Pattern
    # Author Statements
    'TAS': 0.9,  # Traceable Author Statement
    'NAS': 0.3,  # Non-traceable Author Statement
    # Computational Analysis Evidence Codes
    'ISS': -1,  # Sequence/Structural Similarity
    'ISO': -1, # Sequence Orthology
    'ISA': -1, # Sequence Alignment
    'ISM': -1, # Sequence Model
    'IGC': -1, # Genomic Context
    'IBA': -1, # Biological aspect of ancestor
    'IBD': -1, # Biological aspect of descendant
    'IKR': -1, # Key Residues
    'IRD': -1, # Rapid Divergence
    'RCA': -1,  # Reviews Computational Analysis
    # Curator Statement
    'IC' : -1,  # Curator
    'ND' : -1,  # No biological data available
    # Automatically assigned
    'IEA': -1,  # Electronic Annotation
    # Obsolete
    'NR' : -1,  # Not recorded
    # Mystery stuff Barbara included:
    'P'  : -1.0,  # No clue what this is.
    'GOR': -1.0,  # "From reading papers"
    'E'  : -1.0   # No clue what this is.
}
allowed_codes = [p for p,v in evidence_constraints_exp.iteritems() if v > 0]

# In[6]:
db_files = ['/data/mohammad/sifter_data/sifter_webserver/sifter_results_cmp.db']

def run_cmd(db_file,cmd):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(cmd)
    
    result = c.fetchall()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()
    #return cPickle.loads(result[0].encode('ascii','ignore'))
    return result


# In[7]:

def get_results(db_file,my_id):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("select preds,conf_code,start_pos,end_pos,pfam from sifter_results where uniprot_id=?", [my_id])
    
    result = c.fetchall()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()
    #return cPickle.loads(result[0].encode('ascii','ignore'))
    result2=[]
    for res in result:
        res2=list(res)
        res2[0]=cPickle.loads(zlib.decompress(res[0]).encode('ascii','ignore'))
        result2.append(res2)
    return result2

# In[8]:

def get_go_name(goid):
    sql="""SELECT
      term.name 
     FROM   term
     WHERE
       term.acc ='%s'
    """%(goid)
    seq_anns = msql(sql, db_brenner)
    return seq_anns[0]['name']
get_go_name('GO:0005515')


# In[9]:

def Map_id_2_unip(my_id):
    sql="""SELECT
        uniprot_id,
        second_id
     FROM   uniprot_id_map_2
     WHERE
       second_id = '%s'
       AND db = 'UniProtKB-ID'
    """%(my_id)
    #print sql
    # http://wiki.geneontology.org/index.php/Example_Queries
    seq_anns = msql(sql, db_brenner)
    return seq_anns

# In[10]:

def Map_id_2_unip_any(my_id):
    sql="""SELECT
        uniprot_id,
        second_id
     FROM   uniprot_id_map_2
     WHERE
       second_id = '%s'
    """%(my_id)
    #print sql
    # http://wiki.geneontology.org/index.php/Example_Queries
    seq_anns = msql(sql, db_brenner)
    return seq_anns

# In[11]:

def Map_unip_to_any(unip_id):
    sql="""SELECT
        second_id,db
     FROM   uniprot_id_map_2
     WHERE
       uniprot_id = '%s'
    """%(unip_id)
    #print sql
    # http://wiki.geneontology.org/index.php/Example_Queries
    seq_anns = msql(sql, db_brenner)
    return seq_anns

# In[12]:

def Map_unip_to_acc(unip_id):
    sql="""SELECT
        second_id,db
     FROM   uniprot_id_map_2
     WHERE
       uniprot_id = '%s'
       AND db = 'UniProtKB-ID'
    """%(unip_id)
    #print sql
    # http://wiki.geneontology.org/index.php/Example_Queries
    seq_anns = msql(sql, db_brenner)
    return seq_anns


# In[14]:

go_to_idx_file='/lab/app/python/python_mohammad/SIFTER_jobs/webserver/go_to_idx.pickle'
go_file='/lab/app/python/python_mohammad/SIFTER_jobs/workspace/go_daily-termdb.obo-xml'
if not os.path.exists(go_to_idx_file):
    G = readGOoboXML(go_file)
    go_ids=[]
    for i,spec in G.GONameSpace.iteritems():
        if spec=='molecular_function':
            go_ids.append(G.get_goid(i))
    print len(go_ids)
    go_to_idx={go_id:i for i,go_id in enumerate(go_ids)}
    idx_to_go={i:go_id for i,go_id in enumerate(go_ids)}
    pickle.dump([go_to_idx,idx_to_go],open(go_to_idx_file,'w'))   
else:
    [go_to_idx,idx_to_go]=pickle.load(open(go_to_idx_file,'r'))       

def find_processed_results(q_results):
    bads_rn=[]
    q_genes=q_results.keys()
    my_res={}
    for q_gene in q_genes:
        my_res[q_gene]={}
        for res in q_results[q_gene]:
            fam=res[4]
            pos='%s-%s'%(res[2],res[3])
            conf_code=res[1]
            if fam not in my_res[q_gene]:
                my_res[q_gene][fam]={}
            if conf_code not in my_res[q_gene][fam]:
                my_res[q_gene][fam][conf_code]={}
            if pos not in my_res[q_gene][fam][conf_code]:
                my_res[q_gene][fam][conf_code][pos]={}            
            for goid,score in res[0].iteritems():
                if not score is None:
                    my_res[q_gene][fam][conf_code][pos][goid]=score
    return my_res

def find_db_results(db_files,q_genes):
    q_results={}
    for q_gene in q_genes:
        q_res=[]
        for db_file in db_files:
            q_res.extend(get_results(db_file,q_gene))
        q_results[q_gene]=q_res
    my_res=find_processed_results(q_results)
    return my_res

            
def find_results(form):
    input_queries_cleared=form.cleaned_data['input_queries']
    my_genes=input_queries_cleared.split(',')
    my_res=find_db_results(db_files,my_genes)
    return my_res

'''def map_scores_goa(res):
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
    aa={k:ancestors[k] for k in terms}
    all_anc=set([v for w in aa.values() for v in w])
    anc_dict={}
    for t,a in aa.iteritems():
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
        
        if set(todo_list)&(descendants[t]):
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

# In[34]:

def merge_results(results):
    final_res={}
    for res in results:
        w=res[1][0]*res[0] 
        for term,score in res[1][1].iteritems():
            if term not in final_res:
                final_res[term]=0
            final_res[term]+=score*w
    return final_res
            


# In[35]:

def find_res_multidomain(results):
    n_domain=len(results)
    wt=-0.07*log(n_domain)+1
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

# In[36]:
def find_db_results(db_files,q_genes):
    q_results={}
    for q_gene in q_genes:
        q_res=[]
        for db_file in db_files:
            q_res.extend(get_results(db_file,q_gene))
        q_results[q_gene]=q_res
    return q_results


# In[37]:
def find_processed_results(q_results):
    bads_rn=[]
    q_genes=q_results.keys()
    my_res={}
    for q_gene in q_genes:
        my_res[q_gene]={}
        for res in q_results[q_gene]:
            fam=res[4]
            pos='%s-%s'%(res[2],res[3])
            conf_code=res[1]
            if fam not in my_res[q_gene]:
                my_res[q_gene][fam]={}
            if conf_code not in my_res[q_gene][fam]:
                my_res[q_gene][fam][conf_code]={}
            if pos not in my_res[q_gene][fam][conf_code]:
                my_res[q_gene][fam][conf_code][pos]={}            
            for goid,score in res[0].iteritems():
                if not score is None:
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


# In[39]:

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

    return SIFTER_results_merged_MODEL1,MODEL1_my_results,MODEL1_my_results_filtered




# In[40]:

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
    
    return SIFTER_results_merged_MODEL2,MODEL2_my_results,MODEL2_my_results_filtered
   
def find_top_preds(pred_mat,p_genes,thr):
    top_preds={}
    for i in range(pred_mat.shape[0]):
        terms=pred_mat[i,:].nonzero()[1]
        if not terms.tolist():
            print p_genes[i]
            continue
        leaves=[w for w in terms if not(set(descendants[w])&(set(terms)-set([w])))]
        prd=pred_mat[i,leaves]
        mx=max(prd.data)
        prdss=sklearn.preprocessing.binarize(prd, threshold=(mx*thr), copy=True)
        ii=prdss.nonzero()[1]
        leaves=np.array(leaves)[ii]
        top_preds[p_genes[i]]={w:pred_mat[i,w] for w in leaves}
        #ancs=set([v for w in leaves for v in ancestors[w]])-set([rootidx])
    return top_preds
# In[45]:

def find_sifter_preds(q_genes,thr):
    q_results=find_db_results(db_files,q_genes)
    my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
    SIFTER_results_merged_MODEL1,MODEL1_my_results,MODEL1_my_results_filtered=find_Model1_results(SIFTER_results2,real_terms)
    SIFTER_results_merged_MODEL2,MODEL2_my_results,MODEL2_my_results_filtered=find_Model2_results(SIFTER_results2,real_terms)
    predictions_mat_1,p_genes=find_pred_matrix(MODEL1_my_results_filtered)
    predictions_mat_2,p_genes=find_pred_matrix(MODEL2_my_results_filtered)

    top_preds_1=find_top_preds(predictions_mat_1,p_genes,thr)
    top_preds_2=find_top_preds(predictions_mat_2,p_genes,thr)    
    return top_preds_1,top_preds_2
'''    
