from sifter_results_db.models import SifterResults
from termdb.models import Term
from results.models import SIFTER_Output
from django.db import connection
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

def find_db_results(q_genes):

    q_results={}
    for q_gene in q_genes:
        q_res=[]
        for db_file in db_files:
            q_res.extend(get_results(db_file,q_gene))
        q_results[q_gene]=q_res
    return q_results

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

def find_top_preds(preds,thr):
    top_preds={}
    for g,pred in preds.iteritems():
        terms=pred.keys()
        leaves=[w for w in terms if not(set(descendants[w])&(set(terms)-set([w])))]
        tp={w:pred[w] for w in leaves}
        mx=max(tp.values())*thr
        top_preds[g]={w:round(tp[w],2) for w in tp if tp[w]>mx}
        
    return top_preds

def find_sifter_preds(q_genes,thr):
    q_results=find_db_results(q_genes)
    my_res,my_res_all,SIFTER_results,SIFTER_results2,real_terms=find_processed_results(q_results)
    SIFTER_results_merged_MODEL1,MODEL1_my_results,MODEL1_my_results_filtered=find_Model1_results(SIFTER_results2,real_terms)
    SIFTER_results_merged_MODEL2,MODEL2_my_results,MODEL2_my_results_filtered=find_Model2_results(SIFTER_results2,real_terms)
    top_preds_1=find_top_preds(MODEL1_my_results_filtered,thr)
    top_preds_2=find_top_preds(MODEL2_my_results_filtered,thr)    
    return top_preds_1,top_preds_2


def find_results(form):
    my_genes=['A8WRK7_CAEBR']
    tables = connection.introspection.table_names()
    print tables

    print len(SIFTER_Output.objects.filter(n_species=0))
    print len(Term.objects.filter(term_id=11))
    #aa=find_sifter_preds(my_genes,0.75)
    if active_tab=='by_protein':            
            return aa
