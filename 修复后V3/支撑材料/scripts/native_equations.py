"""Small native OMML builder for the paper's reviewed equations.

Supports grouped subscripts/superscripts and fractions, without raster formulas
or Unicode presentation subscripts that some DOCX converters overlap.
"""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import unicodedata

EQUATIONS = {
1: r'F_τ = σ{观测结束时刻 ≤ τ；预报发布时间 ≤ τ；既有采购承诺}',
2: r'A_t + V_t + D_t + Q_t = L_t + C_t + U_t； Q_t,U_t ≥ 0',
3: r'E_{t+1} = E_t + 0.9 C_t − \frac{D_t}{0.9}',
4: r'1200 ≤ E_t ≤ 10800； 0 ≤ C_t,D_t ≤ \frac{5000}{6}',
5: r'X̃_t^s = max{0，X̂_{t|τ} + (X_{h^s} − X̂_{h^s|τ_h})}',
6: r'G_t + D_t − C_t + Q_t^s ≥ L_t^s − V_t^s； Q_t^s ≥ 0， ∀s,t∈H_τ',
7: r'G_t^s=G_t， C_t^s=C_t， D_t^s=D_t， E_t^s=E_t， ∀s',
8: r'min \frac{1}{N_τ} ∑_s ∑_t [p_t^s G_t + 5 p_t^s Q_t^s] + λ|E_{末}−6000| + ε∑_t(C_t+D_t)',
9: r'f_t(x)=p_t x+0.5p_t|x|',
10: r'J_{净} = ∑_t[p_t B_t + f_t(A_t^{末}−B_t) + 5p_t Q_t]',
11: r'J_{逐次} = ∑_t[p_t B_t + ∑_k f_t(A_t^k−A_t^{k−1}) + 5p_t Q_t]',
12: r'J_{逐次}−J_{净} = 0.5∑_t p_t[∑_k|ΔA_t^k|−|∑_k ΔA_t^k|] ≥ 0',
}

def node(tag, children=()):
    n=OxmlElement('m:'+tag)
    for c in children:n.append(c)
    return n

def run(text):
    r=node('r');pr=node('rPr');sty=node('sty');sty.set(qn('m:val'),'p');pr.append(sty);r.append(pr)
    wr=OxmlElement('w:rPr');font=OxmlElement('w:rFonts')
    for k in ['ascii','hAnsi','eastAsia']:font.set(qn('w:'+k),'Arial Unicode MS')
    wr.append(font);size=OxmlElement('w:sz');size.set(qn('w:val'),'20');wr.append(size);r.append(wr)
    t=node('t');t.set(qn('xml:space'),'preserve');t.text=text;r.append(t);return r

def parse(text):
    i=0
    def atom():
        nonlocal i
        if text[i]=='{':
            i+=1;out=sequence(True);return out
        if text.startswith(r'\frac',i):
            i+=5;a=atom();b=atom();return [node('f',[node('num',a),node('den',b)])]
        c=text[i];i+=1
        while i<len(text) and unicodedata.combining(text[i]):c+=text[i];i+=1
        return [run(c)]
    def sequence(group=False):
        nonlocal i
        out=[]
        while i<len(text):
            if group and text[i]=='}':i+=1;return out
            base=atom();sub=sup=None
            while i<len(text) and text[i] in '_^':
                marker=text[i];i+=1;value=atom()
                if marker=='_':sub=value
                else:sup=value
            if sub is not None and sup is not None:out.append(node('sSubSup',[node('e',base),node('sub',sub),node('sup',sup)]))
            elif sub is not None:out.append(node('sSub',[node('e',base),node('sub',sub)]))
            elif sup is not None:out.append(node('sSup',[node('e',base),node('sup',sup)]))
            else:out.extend(base)
        return out
    return sequence()

def equation(number):
    # Literal grouping braces outside scripts are displayed as parentheses.
    source=EQUATIONS[number]
    if number in (1,5):source=source.replace('σ{','σ(').replace('max{','max(');source=source[:-1]+')'
    return node('oMath',parse(source)+[run('  ('+str(number)+')')])
