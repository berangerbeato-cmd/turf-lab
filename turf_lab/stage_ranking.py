"""Position-specific conditional choice model and coherent exact top-k probabilities."""
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import logsumexp


def fit_choice(x, groups, winners, ridge=.01):
    starts=np.r_[0,np.cumsum(groups)[:-1]]
    winners=starts+np.asarray(winners)
    count=len(groups)
    def objective(w):
        s=x@w
        top=np.maximum.reduceat(s,starts)
        e=np.exp(s-np.repeat(top,groups))
        z=np.add.reduceat(e,starts)
        loss=np.mean(np.log(z)+top-s[winners])+ridge*np.dot(w,w)/2
        residual=e/np.repeat(z,groups)
        residual[winners]-=1
        return loss,x.T@residual/count+ridge*w
    result=minimize(objective,np.zeros(x.shape[1]),jac=True,method='L-BFGS-B',
                    options={'maxiter':400,'ftol':1e-10})
    if not result.success:raise ValueError(result.message)
    return result.x,dict(loss=float(result.fun),iterations=int(result.nit))


def temperature(scores,truth,stage):
    def loss(t):
        total=0.
        for s,y in zip(scores,truth):
            keep=[j for j in range(s.shape[1]) if j not in y[:stage]]
            v=s[stage,keep]/t
            total+=logsumexp(v)-s[stage,y[stage]]/t
        return total/len(scores)
    result=minimize_scalar(loss,bounds=(.25,4),method='bounded',options={'xatol':1e-5})
    if not result.success:raise ValueError('Temperature fit failed')
    return float(result.x)


def strengths(scores,temperatures):
    s=np.asarray(scores,dtype=float)/np.asarray(temperatures)[:,None]
    if s.ndim!=2 or not np.isfinite(s).all() or np.any(np.asarray(temperatures)<=0):
        raise ValueError('Invalid scores or temperatures')
    return np.exp(np.maximum(s-s.max(axis=1)[:,None],-700))


def ordered(w,order):
    if len(set(order))!=len(order) or not 0<len(order)<=len(w):raise ValueError('Invalid order')
    remaining=list(range(w.shape[1]));p=1.
    for stage,j in enumerate(order):
        p*=w[stage,j]/w[stage,remaining].sum();remaining.remove(j)
    return float(p)


def unordered(w,selection):
    """Subset dynamic programming sums all permutations, never marginal products."""
    k=len(selection)
    if k not in (3,4,5) or len(set(selection))!=k or min(selection)<0 or max(selection)>=w.shape[1]:raise ValueError('Invalid selection')
    dp=np.zeros(1<<k);dp[0]=1
    for mask in range((1<<k)-1):
        stage=mask.bit_count()
        removed={selection[j] for j in range(k) if mask>>j&1}
        denom=sum(w[stage,j] for j in range(w.shape[1]) if j not in removed)
        for j in range(k):
            if not mask>>j&1:dp[mask|1<<j]+=dp[mask]*w[stage,selection[j]]/denom
    return float(dp[-1])


def greedy(w,k):
    selected=[]
    for stage in range(k):
        selected.append(max((j for j in range(w.shape[1]) if j not in selected),key=lambda j:(w[stage,j],-j)))
    return selected
