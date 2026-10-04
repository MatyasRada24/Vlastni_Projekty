"""Generated from the official BMF PAP 2026. Do not edit; run tools/generate_pap.py.
Source: https://www.bmf-steuerrechner.de/javax.faces.resource/daten/xmls/Lohnsteuer2026.xml.xhtml
SHA256: 24df202e5176d7b8cfd9872fa7a4f54a20333277224cdc236c8ad069bcdcff34
"""
from decimal_math import BigDecimal

class Lohnsteuer2026:
    def __init__(self, **inputs):
        self.af = 1
        self.AJAHR = 0
        self.ALTER1 = 0
        self.ALV = 0
        self.f = 1.0
        self.JFREIB = BigDecimal.ZERO
        self.JHINZU = BigDecimal.ZERO
        self.JRE4 = BigDecimal.ZERO
        self.JRE4ENT = BigDecimal.ZERO
        self.JVBEZ = BigDecimal.ZERO
        self.KRV = 0
        self.KVZ = BigDecimal.ZERO
        self.LZZ = 1
        self.LZZFREIB = BigDecimal.ZERO
        self.LZZHINZU = BigDecimal.ZERO
        self.MBV = BigDecimal.ZERO
        self.PKPV = BigDecimal.ZERO
        self.PKPVAGZ = BigDecimal.ZERO
        self.PKV = 0
        self.PVA = BigDecimal.ZERO
        self.PVS = 0
        self.PVZ = 0
        self.R = 0
        self.RE4 = BigDecimal.ZERO
        self.SONSTB = BigDecimal.ZERO
        self.SONSTENT = BigDecimal.ZERO
        self.STERBE = BigDecimal.ZERO
        self.STKL = 1
        self.VBEZ = BigDecimal.ZERO
        self.VBEZM = BigDecimal.ZERO
        self.VBEZS = BigDecimal.ZERO
        self.VBS = BigDecimal.ZERO
        self.VJAHR = 0
        self.ZKF = BigDecimal.ZERO
        self.ZMVB = 0
        self.BK = BigDecimal.ZERO
        self.BKS = BigDecimal.ZERO
        self.LSTLZZ = BigDecimal.ZERO
        self.SOLZLZZ = BigDecimal.ZERO
        self.SOLZS = BigDecimal.ZERO
        self.STS = BigDecimal.ZERO
        self.VFRB = BigDecimal.ZERO
        self.VFRBS1 = BigDecimal.ZERO
        self.VFRBS2 = BigDecimal.ZERO
        self.WVFRB = BigDecimal.ZERO
        self.WVFRBO = BigDecimal.ZERO
        self.WVFRBM = BigDecimal.ZERO
        self.ALTE = BigDecimal.ZERO
        self.ANP = BigDecimal.ZERO
        self.ANTEIL1 = BigDecimal.ZERO
        self.AVSATZAN = BigDecimal.ZERO
        self.BBGKVPV = BigDecimal.ZERO
        self.BBGRVALV = BigDecimal.ZERO
        self.BMG = BigDecimal.ZERO
        self.DIFF = BigDecimal.ZERO
        self.EFA = BigDecimal.ZERO
        self.FVB = BigDecimal.ZERO
        self.FVBSO = BigDecimal.ZERO
        self.FVBZ = BigDecimal.ZERO
        self.FVBZSO = BigDecimal.ZERO
        self.GFB = BigDecimal.ZERO
        self.HBALTE = BigDecimal.ZERO
        self.HFVB = BigDecimal.ZERO
        self.HFVBZ = BigDecimal.ZERO
        self.HFVBZSO = BigDecimal.ZERO
        self.HOCH = BigDecimal.ZERO
        self.J = 0
        self.JBMG = BigDecimal.ZERO
        self.JLFREIB = BigDecimal.ZERO
        self.JLHINZU = BigDecimal.ZERO
        self.JW = BigDecimal.ZERO
        self.K = 0
        self.KFB = BigDecimal.ZERO
        self.KVSATZAN = BigDecimal.ZERO
        self.KZTAB = 0
        self.LSTJAHR = BigDecimal.ZERO
        self.LSTOSO = BigDecimal.ZERO
        self.LSTSO = BigDecimal.ZERO
        self.MIST = BigDecimal.ZERO
        self.PKPVAGZJ = BigDecimal.ZERO
        self.PVSATZAN = BigDecimal.ZERO
        self.RVSATZAN = BigDecimal.ZERO
        self.RW = BigDecimal.ZERO
        self.SAP = BigDecimal.ZERO
        self.SOLZFREI = BigDecimal.ZERO
        self.SOLZJ = BigDecimal.ZERO
        self.SOLZMIN = BigDecimal.ZERO
        self.SOLZSBMG = BigDecimal.ZERO
        self.SOLZSZVE = BigDecimal.ZERO
        self.ST = BigDecimal.ZERO
        self.ST1 = BigDecimal.ZERO
        self.ST2 = BigDecimal.ZERO
        self.VBEZB = BigDecimal.ZERO
        self.VBEZBSO = BigDecimal.ZERO
        self.VERGL = BigDecimal.ZERO
        self.VSPHB = BigDecimal.ZERO
        self.VSP = BigDecimal.ZERO
        self.VSPN = BigDecimal.ZERO
        self.VSPALV = BigDecimal.ZERO
        self.VSPKVPV = BigDecimal.ZERO
        self.VSPR = BigDecimal.ZERO
        self.W1STKL5 = BigDecimal.ZERO
        self.W2STKL5 = BigDecimal.ZERO
        self.W3STKL5 = BigDecimal.ZERO
        self.X = BigDecimal.ZERO
        self.Y = BigDecimal.ZERO
        self.ZRE4 = BigDecimal.ZERO
        self.ZRE4J = BigDecimal.ZERO
        self.ZRE4VP = BigDecimal.ZERO
        self.ZRE4VPR = BigDecimal.ZERO
        self.ZTABFB = BigDecimal.ZERO
        self.ZVBEZ = BigDecimal.ZERO
        self.ZVBEZJ = BigDecimal.ZERO
        self.ZVE = BigDecimal.ZERO
        self.ZX = BigDecimal.ZERO
        self.ZZX = BigDecimal.ZERO
        self.TAB1 = [BigDecimal.ZERO, BigDecimal.valueOf( 0.4), BigDecimal.valueOf( 0.384), BigDecimal.valueOf( 0.368), BigDecimal.valueOf( 0.352), BigDecimal.valueOf( 0.336), BigDecimal.valueOf( 0.32), BigDecimal.valueOf( 0.304), BigDecimal.valueOf( 0.288), BigDecimal.valueOf( 0.272), BigDecimal.valueOf( 0.256), BigDecimal.valueOf( 0.24), BigDecimal.valueOf( 0.224), BigDecimal.valueOf( 0.208), BigDecimal.valueOf( 0.192), BigDecimal.valueOf( 0.176), BigDecimal.valueOf( 0.16), BigDecimal.valueOf( 0.152), BigDecimal.valueOf( 0.144), BigDecimal.valueOf( 0.14), BigDecimal.valueOf( 0.136), BigDecimal.valueOf( 0.132), BigDecimal.valueOf( 0.128), BigDecimal.valueOf( 0.124), BigDecimal.valueOf( 0.12), BigDecimal.valueOf( 0.116), BigDecimal.valueOf( 0.112), BigDecimal.valueOf( 0.108), BigDecimal.valueOf( 0.104), BigDecimal.valueOf( 0.1), BigDecimal.valueOf( 0.096), BigDecimal.valueOf( 0.092), BigDecimal.valueOf( 0.088), BigDecimal.valueOf( 0.084), BigDecimal.valueOf( 0.08), BigDecimal.valueOf( 0.076), BigDecimal.valueOf( 0.072), BigDecimal.valueOf( 0.068), BigDecimal.valueOf( 0.064), BigDecimal.valueOf( 0.06), BigDecimal.valueOf( 0.056), BigDecimal.valueOf( 0.052), BigDecimal.valueOf( 0.048), BigDecimal.valueOf( 0.044), BigDecimal.valueOf( 0.04), BigDecimal.valueOf( 0.036), BigDecimal.valueOf( 0.032), BigDecimal.valueOf( 0.028), BigDecimal.valueOf( 0.024), BigDecimal.valueOf( 0.02), BigDecimal.valueOf( 0.016), BigDecimal.valueOf( 0.012), BigDecimal.valueOf( 0.008), BigDecimal.valueOf( 0.004), BigDecimal.valueOf( 0)]
        self.TAB2 = [BigDecimal.ZERO, BigDecimal.valueOf( 3000), BigDecimal.valueOf( 2880), BigDecimal.valueOf( 2760), BigDecimal.valueOf( 2640), BigDecimal.valueOf( 2520), BigDecimal.valueOf( 2400), BigDecimal.valueOf( 2280), BigDecimal.valueOf( 2160), BigDecimal.valueOf( 2040), BigDecimal.valueOf( 1920), BigDecimal.valueOf( 1800), BigDecimal.valueOf( 1680), BigDecimal.valueOf( 1560), BigDecimal.valueOf( 1440), BigDecimal.valueOf( 1320), BigDecimal.valueOf( 1200), BigDecimal.valueOf( 1140), BigDecimal.valueOf( 1080), BigDecimal.valueOf( 1050), BigDecimal.valueOf( 1020), BigDecimal.valueOf( 990), BigDecimal.valueOf( 960), BigDecimal.valueOf( 930), BigDecimal.valueOf( 900), BigDecimal.valueOf( 870), BigDecimal.valueOf( 840), BigDecimal.valueOf( 810), BigDecimal.valueOf( 780), BigDecimal.valueOf( 750), BigDecimal.valueOf( 720), BigDecimal.valueOf( 690), BigDecimal.valueOf( 660), BigDecimal.valueOf( 630), BigDecimal.valueOf( 600), BigDecimal.valueOf( 570), BigDecimal.valueOf( 540), BigDecimal.valueOf( 510), BigDecimal.valueOf( 480), BigDecimal.valueOf( 450), BigDecimal.valueOf( 420), BigDecimal.valueOf( 390), BigDecimal.valueOf( 360), BigDecimal.valueOf( 330), BigDecimal.valueOf( 300), BigDecimal.valueOf( 270), BigDecimal.valueOf( 240), BigDecimal.valueOf( 210), BigDecimal.valueOf( 180), BigDecimal.valueOf( 150), BigDecimal.valueOf( 120), BigDecimal.valueOf( 90), BigDecimal.valueOf( 60), BigDecimal.valueOf( 30), BigDecimal.valueOf( 0) ]
        self.TAB3 = [BigDecimal.ZERO, BigDecimal.valueOf( 900), BigDecimal.valueOf( 864), BigDecimal.valueOf( 828), BigDecimal.valueOf( 792), BigDecimal.valueOf( 756), BigDecimal.valueOf( 720), BigDecimal.valueOf( 684), BigDecimal.valueOf( 648), BigDecimal.valueOf( 612), BigDecimal.valueOf( 576), BigDecimal.valueOf( 540), BigDecimal.valueOf( 504), BigDecimal.valueOf( 468), BigDecimal.valueOf( 432), BigDecimal.valueOf( 396), BigDecimal.valueOf( 360), BigDecimal.valueOf( 342), BigDecimal.valueOf( 324), BigDecimal.valueOf( 315), BigDecimal.valueOf( 306), BigDecimal.valueOf( 297), BigDecimal.valueOf( 288), BigDecimal.valueOf( 279), BigDecimal.valueOf( 270), BigDecimal.valueOf( 261), BigDecimal.valueOf( 252), BigDecimal.valueOf( 243), BigDecimal.valueOf( 234), BigDecimal.valueOf( 225), BigDecimal.valueOf( 216), BigDecimal.valueOf( 207), BigDecimal.valueOf( 198), BigDecimal.valueOf( 189), BigDecimal.valueOf( 180), BigDecimal.valueOf( 171), BigDecimal.valueOf( 162), BigDecimal.valueOf( 153), BigDecimal.valueOf( 144), BigDecimal.valueOf( 135), BigDecimal.valueOf( 126), BigDecimal.valueOf( 117), BigDecimal.valueOf( 108), BigDecimal.valueOf( 99), BigDecimal.valueOf( 90), BigDecimal.valueOf( 81), BigDecimal.valueOf( 72), BigDecimal.valueOf( 63), BigDecimal.valueOf( 54), BigDecimal.valueOf( 45), BigDecimal.valueOf( 36), BigDecimal.valueOf( 27), BigDecimal.valueOf( 18), BigDecimal.valueOf( 9), BigDecimal.valueOf( 0)]
        self.TAB4 = [BigDecimal.ZERO, BigDecimal.valueOf( 0.4), BigDecimal.valueOf( 0.384), BigDecimal.valueOf( 0.368), BigDecimal.valueOf( 0.352), BigDecimal.valueOf( 0.336), BigDecimal.valueOf( 0.32), BigDecimal.valueOf( 0.304), BigDecimal.valueOf( 0.288), BigDecimal.valueOf( 0.272), BigDecimal.valueOf( 0.256), BigDecimal.valueOf( 0.24), BigDecimal.valueOf( 0.224), BigDecimal.valueOf( 0.208), BigDecimal.valueOf( 0.192), BigDecimal.valueOf( 0.176), BigDecimal.valueOf( 0.16), BigDecimal.valueOf( 0.152), BigDecimal.valueOf( 0.144), BigDecimal.valueOf( 0.14), BigDecimal.valueOf( 0.136), BigDecimal.valueOf( 0.132), BigDecimal.valueOf( 0.128), BigDecimal.valueOf( 0.124), BigDecimal.valueOf( 0.12), BigDecimal.valueOf( 0.116), BigDecimal.valueOf( 0.112), BigDecimal.valueOf( 0.108), BigDecimal.valueOf( 0.104), BigDecimal.valueOf( 0.1), BigDecimal.valueOf( 0.096), BigDecimal.valueOf( 0.092), BigDecimal.valueOf( 0.088), BigDecimal.valueOf( 0.084), BigDecimal.valueOf( 0.08), BigDecimal.valueOf( 0.076), BigDecimal.valueOf( 0.072), BigDecimal.valueOf( 0.068), BigDecimal.valueOf( 0.064), BigDecimal.valueOf( 0.06), BigDecimal.valueOf( 0.056), BigDecimal.valueOf( 0.052), BigDecimal.valueOf( 0.048), BigDecimal.valueOf( 0.044), BigDecimal.valueOf( 0.04), BigDecimal.valueOf( 0.036), BigDecimal.valueOf( 0.032), BigDecimal.valueOf( 0.028), BigDecimal.valueOf( 0.024), BigDecimal.valueOf( 0.02), BigDecimal.valueOf( 0.016), BigDecimal.valueOf( 0.012), BigDecimal.valueOf( 0.008), BigDecimal.valueOf( 0.004), BigDecimal.valueOf( 0)]
        self.TAB5 = [BigDecimal.ZERO, BigDecimal.valueOf( 1900), BigDecimal.valueOf( 1824), BigDecimal.valueOf( 1748), BigDecimal.valueOf( 1672), BigDecimal.valueOf( 1596), BigDecimal.valueOf( 1520), BigDecimal.valueOf( 1444), BigDecimal.valueOf( 1368), BigDecimal.valueOf( 1292), BigDecimal.valueOf( 1216), BigDecimal.valueOf( 1140), BigDecimal.valueOf( 1064), BigDecimal.valueOf( 988), BigDecimal.valueOf( 912), BigDecimal.valueOf( 836), BigDecimal.valueOf( 760), BigDecimal.valueOf( 722), BigDecimal.valueOf( 684), BigDecimal.valueOf( 665), BigDecimal.valueOf( 646), BigDecimal.valueOf( 627), BigDecimal.valueOf( 608), BigDecimal.valueOf( 589), BigDecimal.valueOf( 570), BigDecimal.valueOf( 551), BigDecimal.valueOf( 532), BigDecimal.valueOf( 513), BigDecimal.valueOf( 494), BigDecimal.valueOf( 475), BigDecimal.valueOf( 456), BigDecimal.valueOf( 437), BigDecimal.valueOf( 418), BigDecimal.valueOf( 399), BigDecimal.valueOf( 380), BigDecimal.valueOf( 361), BigDecimal.valueOf( 342), BigDecimal.valueOf( 323), BigDecimal.valueOf( 304), BigDecimal.valueOf( 285), BigDecimal.valueOf( 266), BigDecimal.valueOf( 247), BigDecimal.valueOf( 228), BigDecimal.valueOf( 209), BigDecimal.valueOf( 190), BigDecimal.valueOf( 171), BigDecimal.valueOf( 152), BigDecimal.valueOf( 133), BigDecimal.valueOf( 114), BigDecimal.valueOf( 95), BigDecimal.valueOf( 76), BigDecimal.valueOf( 57), BigDecimal.valueOf( 38), BigDecimal.valueOf( 19), BigDecimal.valueOf( 0)]
        self.ZAHL1 = BigDecimal.ONE
        self.ZAHL2 = BigDecimal.valueOf(2)
        self.ZAHL5 = BigDecimal.valueOf(5)
        self.ZAHL7 = BigDecimal.valueOf(7)
        self.ZAHL12 = BigDecimal.valueOf(12)
        self.ZAHL100 = BigDecimal.valueOf(100)
        self.ZAHL360 = BigDecimal.valueOf(360)
        self.ZAHL500 = BigDecimal.valueOf(500)
        self.ZAHL700 = BigDecimal.valueOf(700)
        self.ZAHL1000 = BigDecimal.valueOf(1000)
        self.ZAHL10000 = BigDecimal.valueOf(10000)
        types = {'af': 'int', 'AJAHR': 'int', 'ALTER1': 'int', 'ALV': 'int', 'f': 'double', 'JFREIB': 'BigDecimal', 'JHINZU': 'BigDecimal', 'JRE4': 'BigDecimal', 'JRE4ENT': 'BigDecimal', 'JVBEZ': 'BigDecimal', 'KRV': 'int', 'KVZ': 'BigDecimal', 'LZZ': 'int', 'LZZFREIB': 'BigDecimal', 'LZZHINZU': 'BigDecimal', 'MBV': 'BigDecimal', 'PKPV': 'BigDecimal', 'PKPVAGZ': 'BigDecimal', 'PKV': 'int', 'PVA': 'BigDecimal', 'PVS': 'int', 'PVZ': 'int', 'R': 'int', 'RE4': 'BigDecimal', 'SONSTB': 'BigDecimal', 'SONSTENT': 'BigDecimal', 'STERBE': 'BigDecimal', 'STKL': 'int', 'VBEZ': 'BigDecimal', 'VBEZM': 'BigDecimal', 'VBEZS': 'BigDecimal', 'VBS': 'BigDecimal', 'VJAHR': 'int', 'ZKF': 'BigDecimal', 'ZMVB': 'int'}
        for name, value in inputs.items():
            if name not in types:
                raise ValueError(f"Unknown PAP input: {name}")
            setattr(self, name, BigDecimal(value) if types[name] == "BigDecimal" else value)

    def calculate(self):
        self.MPARA()
        self.MRE4JL()
        self.VBEZBSO= BigDecimal.ZERO
        self.MRE4()
        self.MRE4ABZ()
        self.MBERECH()
        self.MSONST()
        return self

    def MPARA(self):
        self.BBGRVALV = BigDecimal.valueOf(101400)
        self.AVSATZAN = BigDecimal.valueOf(0.013)
        self.RVSATZAN = BigDecimal.valueOf(0.093)
        self.BBGKVPV = BigDecimal.valueOf(69750)
        self.KVSATZAN = (self.KVZ.divide(self.ZAHL2).divide(self.ZAHL100)).add(BigDecimal.valueOf(0.07))
        if self.PVS == 1:
            self.PVSATZAN = BigDecimal.valueOf(0.023)
        else:
            self.PVSATZAN =  BigDecimal.valueOf(0.018)
        if self.PVZ == 1:
            self.PVSATZAN = self.PVSATZAN.add(BigDecimal.valueOf(0.006))
        else:
            self.PVSATZAN = self.PVSATZAN.subtract(self.PVA.multiply(BigDecimal.valueOf(0.0025)))
        self.W1STKL5 = BigDecimal.valueOf(14071)
        self.W2STKL5 = BigDecimal.valueOf(34939)
        self.W3STKL5 = BigDecimal.valueOf(222260)
        self.GFB = BigDecimal.valueOf(12348)
        self.SOLZFREI = BigDecimal.valueOf(20350)

    def MRE4JL(self):
        if self.LZZ == 1:
            self.ZRE4J= self.RE4.divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            self.ZVBEZJ= self.VBEZ.divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            self.JLFREIB= self.LZZFREIB.divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            self.JLHINZU= self.LZZHINZU.divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        else:
            if self.LZZ == 2:
                self.ZRE4J= (self.RE4.multiply (self.ZAHL12)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                self.ZVBEZJ= (self.VBEZ.multiply (self.ZAHL12)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                self.JLFREIB= (self.LZZFREIB.multiply (self.ZAHL12)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                self.JLHINZU= (self.LZZHINZU.multiply (self.ZAHL12)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
            else:
                if self.LZZ == 3:
                    self.ZRE4J= (self.RE4.multiply (self.ZAHL360)).divide (self.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                    self.ZVBEZJ= (self.VBEZ.multiply (self.ZAHL360)).divide (self.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                    self.JLFREIB= (self.LZZFREIB.multiply (self.ZAHL360)).divide (self.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                    self.JLHINZU= (self.LZZHINZU.multiply (self.ZAHL360)).divide (self.ZAHL700, 2, BigDecimal.ROUND_DOWN)
                else:
                    self.ZRE4J= (self.RE4.multiply (self.ZAHL360)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                    self.ZVBEZJ= (self.VBEZ.multiply (self.ZAHL360)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                    self.JLFREIB= (self.LZZFREIB.multiply (self.ZAHL360)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
                    self.JLHINZU= (self.LZZHINZU.multiply (self.ZAHL360)).divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        if self.af == 0:
            self.f= 1

    def MRE4(self):
        if self.ZVBEZJ.compareTo (BigDecimal.ZERO) == 0:
            self.FVBZ= BigDecimal.ZERO
            self.FVB= BigDecimal.ZERO
            self.FVBZSO= BigDecimal.ZERO
            self.FVBSO= BigDecimal.ZERO
        else:
            if self.VJAHR < 2006:
                self.J= 1
            else:
                if self.VJAHR < 2058:
                    self.J= self.VJAHR - 2004
                else:
                    self.J= 54
            if self.LZZ == 1:
                self.VBEZB= (self.VBEZM.multiply (BigDecimal.valueOf(self.ZMVB))).add (self.VBEZS)
                self.HFVB= self.TAB2[self.J].divide (self.ZAHL12).multiply (BigDecimal.valueOf(self.ZMVB)).setScale (0, BigDecimal.ROUND_UP)
                self.FVBZ= self.TAB3[self.J].divide (self.ZAHL12).multiply (BigDecimal.valueOf(self.ZMVB)).setScale (0, BigDecimal.ROUND_UP)
            else:
                self.VBEZB= ((self.VBEZM.multiply (self.ZAHL12)).add (self.VBEZS)).setScale (2, BigDecimal.ROUND_DOWN)
                self.HFVB= self.TAB2[self.J]
                self.FVBZ= self.TAB3[self.J]
            self.FVB= ((self.VBEZB.multiply (self.TAB1[self.J]))).divide (self.ZAHL100).setScale (2, BigDecimal.ROUND_UP)
            if self.FVB.compareTo (self.HFVB) == 1:
                self.FVB = self.HFVB
            if self.FVB.compareTo (self.ZVBEZJ) == 1:
                self.FVB = self.ZVBEZJ
            self.FVBSO= (self.FVB.add((self.VBEZBSO.multiply (self.TAB1[self.J])).divide (self.ZAHL100))).setScale (2, BigDecimal.ROUND_UP)
            if self.FVBSO.compareTo (self.TAB2[self.J]) == 1:
                self.FVBSO = self.TAB2[self.J]
            self.HFVBZSO= (((self.VBEZB.add(self.VBEZBSO)).divide (self.ZAHL100)).subtract (self.FVBSO)).setScale (2, BigDecimal.ROUND_DOWN)
            self.FVBZSO= (self.FVBZ.add((self.VBEZBSO).divide (self.ZAHL100))).setScale (0, BigDecimal.ROUND_UP)
            if self.FVBZSO.compareTo (self.HFVBZSO) == 1:
                self.FVBZSO = self.HFVBZSO.setScale(0, BigDecimal.ROUND_UP)
            if self.FVBZSO.compareTo (self.TAB3[self.J]) == 1:
                self.FVBZSO = self.TAB3[self.J]
            self.HFVBZ= ((self.VBEZB.divide (self.ZAHL100)).subtract (self.FVB)).setScale (2, BigDecimal.ROUND_DOWN)
            if self.FVBZ.compareTo (self.HFVBZ) == 1:
                self.FVBZ = self.HFVBZ.setScale (0, BigDecimal.ROUND_UP)
        self.MRE4ALTE()

    def MRE4ALTE(self):
        if self.ALTER1 == 0:
            self.ALTE= BigDecimal.ZERO
        else:
            if self.AJAHR < 2006:
                self.K= 1
            else:
                if self.AJAHR < 2058:
                    self.K= self.AJAHR - 2004
                else:
                    self.K= 54
            self.BMG= self.ZRE4J.subtract (self.ZVBEZJ)
            self.ALTE = (self.BMG.multiply(self.TAB4[self.K])).setScale(0, BigDecimal.ROUND_UP)
            self.HBALTE= self.TAB5[self.K]
            if self.ALTE.compareTo (self.HBALTE) == 1:
                self.ALTE= self.HBALTE

    def MRE4ABZ(self):
        self.ZRE4= (self.ZRE4J.subtract (self.FVB).subtract   (self.ALTE).subtract (self.JLFREIB).add (self.JLHINZU)).setScale (2, BigDecimal.ROUND_DOWN)
        if self.ZRE4.compareTo (BigDecimal.ZERO) == -1:
            self.ZRE4= BigDecimal.ZERO
        self.ZRE4VP= self.ZRE4J
        self.ZVBEZ = self.ZVBEZJ.subtract(self.FVB).setScale(2, BigDecimal.ROUND_DOWN)
        if self.ZVBEZ.compareTo(BigDecimal.ZERO) == -1:
            self.ZVBEZ = BigDecimal.ZERO

    def MBERECH(self):
        self.MZTABFB()
        self.VFRB = ((self.ANP.add(self.FVB.add(self.FVBZ))).multiply(self.ZAHL100)).setScale(0, BigDecimal.ROUND_DOWN)
        self.MLSTJAHR()
        self.WVFRB = ((self.ZVE.subtract(self.GFB)).multiply(self.ZAHL100)).setScale(0, BigDecimal.ROUND_DOWN)
        if self.WVFRB.compareTo(BigDecimal.ZERO) == -1:
            self.WVFRB = BigDecimal.ZERO
        self.LSTJAHR = (self.ST.multiply(BigDecimal.valueOf(self.f))).setScale(0,BigDecimal.ROUND_DOWN)
        self.UPLSTLZZ()
        if self.ZKF.compareTo(BigDecimal.ZERO) == 1:
            self.ZTABFB = self.ZTABFB.add(self.KFB)
            self.MRE4ABZ()
            self.MLSTJAHR()
            self.JBMG = (self.ST.multiply(BigDecimal.valueOf(self.f))).setScale(0,BigDecimal.ROUND_DOWN)
        else:
            self.JBMG = self.LSTJAHR
        self.MSOLZ()

    def MZTABFB(self):
        self.ANP= BigDecimal.ZERO
        if self.ZVBEZ.compareTo (BigDecimal.ZERO) >= 0  and  self.ZVBEZ.compareTo(self.FVBZ) == -1:
            self.FVBZ = BigDecimal.valueOf(self.ZVBEZ.longValue())
        if self.STKL < 6:
            if self.ZVBEZ.compareTo (BigDecimal.ZERO) == 1:
                if (self.ZVBEZ.subtract (self.FVBZ)).compareTo (BigDecimal.valueOf(102)) == -1:
                    self.ANP= (self.ZVBEZ.subtract (self.FVBZ)).setScale (0, BigDecimal.ROUND_UP)
                else:
                    self.ANP= BigDecimal.valueOf(102)
        else:
            self.FVBZ= BigDecimal.ZERO
            self.FVBZSO= BigDecimal.ZERO
        if self.STKL < 6:
            if self.ZRE4.compareTo(self.ZVBEZ) == 1:
                if self.ZRE4.subtract(self.ZVBEZ).compareTo(BigDecimal.valueOf(1230)) == -1:
                    self.ANP = self.ANP.add(self.ZRE4).subtract(self.ZVBEZ).setScale(0,BigDecimal.ROUND_UP)
                else:
                    self.ANP = self.ANP.add(BigDecimal.valueOf(1230))
        self.KZTAB= 1
        if self.STKL == 1:
            self.SAP= BigDecimal.valueOf(36)
            self.KFB= (self.ZKF.multiply (BigDecimal.valueOf(9756))).setScale (0, BigDecimal.ROUND_DOWN)
        else:
            if self.STKL == 2:
                self.EFA= BigDecimal.valueOf(4260)
                self.SAP= BigDecimal.valueOf(36)
                self.KFB= (self.ZKF.multiply (BigDecimal.valueOf(9756))).setScale (0, BigDecimal.ROUND_DOWN)
            else:
                if self.STKL == 3:
                    self.KZTAB= 2
                    self.SAP= BigDecimal.valueOf(36)
                    self.KFB= (self.ZKF.multiply (BigDecimal.valueOf(9756))).setScale (0, BigDecimal.ROUND_DOWN)
                else:
                    if self.STKL == 4:
                        self.SAP= BigDecimal.valueOf(36)
                        self.KFB= (self.ZKF.multiply (BigDecimal.valueOf(4878))).setScale (0, BigDecimal.ROUND_DOWN)
                    else:
                        if self.STKL == 5:
                            self.SAP= BigDecimal.valueOf(36)
                            self.KFB= BigDecimal.ZERO
                        else:
                            self.KFB= BigDecimal.ZERO
        self.ZTABFB= (self.EFA.add (self.ANP).add (self.SAP).add (self.FVBZ)).setScale (2, BigDecimal.ROUND_DOWN)

    def MLSTJAHR(self):
        self.UPEVP()
        self.ZVE= self.ZRE4.subtract (self.ZTABFB).subtract(self.VSP)
        self.UPMLST()

    def UPLSTLZZ(self):
        self.JW = self.LSTJAHR.multiply(self.ZAHL100)
        self.UPANTEIL()
        self.LSTLZZ = self.ANTEIL1

    def UPMLST(self):
        if self.ZVE.compareTo (self.ZAHL1) == -1:
            self.ZVE= BigDecimal.ZERO
            self.X= BigDecimal.ZERO
        else:
            self.X= (self.ZVE.divide (BigDecimal.valueOf(self.KZTAB))).setScale (0, BigDecimal.ROUND_DOWN)
        if self.STKL < 5:
            self.UPTAB26()
        else:
            self.MST5_6()

    def UPEVP(self):
        if self.KRV == 1:
            self.VSPR = BigDecimal.ZERO
        else:
            if self.ZRE4VP.compareTo(self.BBGRVALV) == 1:
                self.ZRE4VPR = self.BBGRVALV
            else:
                self.ZRE4VPR = self.ZRE4VP
            self.VSPR = (self.ZRE4VPR.multiply(self.RVSATZAN)).setScale(2,BigDecimal.ROUND_DOWN)
        self.MVSPKVPV()
        if self.ALV == 1:
            pass
        else:
            if self.STKL == 6:
                pass
            else:
                self.MVSPHB()

    def MVSPKVPV(self):
        if self.ZRE4VP.compareTo(self.BBGKVPV) == 1:
            self.ZRE4VPR = self.BBGKVPV
        else:
            self.ZRE4VPR = self.ZRE4VP
        if self.PKV > 0:
            if self.STKL == 6:
                self.VSPKVPV = BigDecimal.ZERO
            else:
                self.PKPVAGZJ = self.PKPVAGZ.multiply(self.ZAHL12).divide(self.ZAHL100).setScale(2,BigDecimal.ROUND_DOWN)
                self.VSPKVPV = self.PKPV.multiply(self.ZAHL12).divide(self.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
                self.VSPKVPV = self.VSPKVPV.subtract(self.PKPVAGZJ)
                if self.VSPKVPV.compareTo(BigDecimal.ZERO) == -1:
                    self.VSPKVPV = BigDecimal.ZERO
        else:
            self.VSPKVPV = self.ZRE4VPR.multiply(self.KVSATZAN.add(self.PVSATZAN)).setScale(2, BigDecimal.ROUND_DOWN)
        self.VSP = self.VSPKVPV.add(self.VSPR).setScale(0, BigDecimal.ROUND_UP)

    def MVSPHB(self):
        if self.ZRE4VP.compareTo(self.BBGRVALV) == 1:
            self.ZRE4VPR = self.BBGRVALV
        else:
            self.ZRE4VPR = self.ZRE4VP
        self.VSPALV = self.AVSATZAN.multiply(self.ZRE4VPR).setScale(2, BigDecimal.ROUND_DOWN)
        self.VSPHB = self.VSPALV.add(self.VSPKVPV).setScale(2, BigDecimal.ROUND_DOWN)
        if self.VSPHB.compareTo(BigDecimal.valueOf(1900)) == 1:
            self.VSPHB = BigDecimal.valueOf(1900)
        self.VSPN = self.VSPR.add(self.VSPHB).setScale(0, BigDecimal.ROUND_UP)
        if self.VSPN.compareTo(self.VSP) == 1:
            self.VSP = self.VSPN

    def MST5_6(self):
        self.ZZX= self.X
        if self.ZZX.compareTo(self.W2STKL5) == 1:
            self.ZX= self.W2STKL5
            self.UP5_6()
            if self.ZZX.compareTo (self.W3STKL5) == 1:
                self.ST= (self.ST.add ((self.W3STKL5.subtract (self.W2STKL5)).multiply (BigDecimal.valueOf(0.42)))).setScale (0, BigDecimal.ROUND_DOWN)
                self.ST= (self.ST.add ((self.ZZX.subtract (self.W3STKL5)).multiply (BigDecimal.valueOf(0.45)))).setScale (0, BigDecimal.ROUND_DOWN)
            else:
                self.ST= (self.ST.add ((self.ZZX.subtract (self.W2STKL5)).multiply (BigDecimal.valueOf(0.42)))).setScale (0, BigDecimal.ROUND_DOWN)
        else:
            self.ZX= self.ZZX
            self.UP5_6()
            if self.ZZX.compareTo (self.W1STKL5) == 1:
                self.VERGL= self.ST
                self.ZX= self.W1STKL5
                self.UP5_6()
                self.HOCH= (self.ST.add ((self.ZZX.subtract (self.W1STKL5)).multiply (BigDecimal.valueOf(0.42)))).setScale (0, BigDecimal.ROUND_DOWN)
                if self.HOCH.compareTo (self.VERGL) == -1:
                    self.ST= self.HOCH
                else:
                    self.ST= self.VERGL

    def UP5_6(self):
        self.X= (self.ZX.multiply (BigDecimal.valueOf(1.25))).setScale (0, BigDecimal.ROUND_DOWN)
        self.UPTAB26()
        self.ST1= self.ST
        self.X= (self.ZX.multiply (BigDecimal.valueOf(0.75))).setScale (0, BigDecimal.ROUND_DOWN)
        self.UPTAB26()
        self.ST2= self.ST
        self.DIFF= (self.ST1.subtract (self.ST2)).multiply (self.ZAHL2)
        self.MIST= (self.ZX.multiply (BigDecimal.valueOf(0.14))).setScale (0, BigDecimal.ROUND_DOWN)
        if self.MIST.compareTo (self.DIFF) == 1:
            self.ST= self.MIST
        else:
            self.ST= self.DIFF

    def MSOLZ(self):
        self.SOLZFREI = (self.SOLZFREI.multiply(BigDecimal.valueOf(self.KZTAB)))
        if self.JBMG.compareTo (self.SOLZFREI) == 1:
            self.SOLZJ= (self.JBMG.multiply (BigDecimal.valueOf(5.5))).divide(self.ZAHL100).setScale(2, BigDecimal.ROUND_DOWN)
            self.SOLZMIN= (self.JBMG.subtract (self.SOLZFREI)).multiply (BigDecimal.valueOf(11.9)).divide (self.ZAHL100).setScale (2, BigDecimal.ROUND_DOWN)
            if self.SOLZMIN.compareTo (self.SOLZJ) == -1:
                self.SOLZJ= self.SOLZMIN
            self.JW= self.SOLZJ.multiply (self.ZAHL100).setScale (0, BigDecimal.ROUND_DOWN)
            self.UPANTEIL()
            self.SOLZLZZ= self.ANTEIL1
        else:
            self.SOLZLZZ= BigDecimal.ZERO
        if self.R > 0:
            self.JW= self.JBMG.multiply (self.ZAHL100)
            self.UPANTEIL()
            self.BK= self.ANTEIL1
        else:
            self.BK= BigDecimal.ZERO

    def UPANTEIL(self):
        if self.LZZ == 1:
            self.ANTEIL1= self.JW
        else:
            if self.LZZ == 2:
                self.ANTEIL1= self.JW.divide (self.ZAHL12, 0, BigDecimal.ROUND_DOWN)
            else:
                if self.LZZ == 3:
                    self.ANTEIL1= (self.JW.multiply (self.ZAHL7)).divide (self.ZAHL360, 0, BigDecimal.ROUND_DOWN)
                else:
                    self.ANTEIL1= self.JW.divide (self.ZAHL360, 0, BigDecimal.ROUND_DOWN)

    def MSONST(self):
        self.LZZ = 1
        if self.ZMVB == 0:
            self.ZMVB = 12
        if self.SONSTB.compareTo (BigDecimal.ZERO) == 0  and  self.MBV.compareTo (BigDecimal.ZERO) == 0:
            self.LSTSO= BigDecimal.ZERO
            self.STS= BigDecimal.ZERO
            self.SOLZS= BigDecimal.ZERO
            self.BKS= BigDecimal.ZERO
        else:
            self.MOSONST()
            self.ZRE4J= ((self.JRE4.add (self.SONSTB)).divide (self.ZAHL100)).setScale (2, BigDecimal.ROUND_DOWN)
            self.ZVBEZJ= ((self.JVBEZ.add (self.VBS)).divide (self.ZAHL100)).setScale (2, BigDecimal.ROUND_DOWN)
            self.VBEZBSO= self.STERBE
            self.MRE4SONST()
            self.MLSTJAHR()
            self.WVFRBM = (self.ZVE.subtract(self.GFB)).multiply(self.ZAHL100).setScale(2,BigDecimal.ROUND_DOWN)
            if self.WVFRBM.compareTo(BigDecimal.ZERO) == -1:
                self.WVFRBM = BigDecimal.ZERO
            self.LSTSO= self.ST.multiply (self.ZAHL100)
            self.STS = self.LSTSO.subtract(self.LSTOSO).multiply(BigDecimal.valueOf(self.f)).divide(self.ZAHL100, 0, BigDecimal.ROUND_DOWN).multiply(self.ZAHL100)
            self.STSMIN()

    def STSMIN(self):
        if self.STS.compareTo(BigDecimal.ZERO) == -1:
            if self.MBV.compareTo(BigDecimal.ZERO) == 0:
                pass
            else:
                self.LSTLZZ = self.LSTLZZ.add(self.STS)
                if self.LSTLZZ.compareTo(BigDecimal.ZERO) == -1:
                    self.LSTLZZ = BigDecimal.ZERO
                self.SOLZLZZ = self.SOLZLZZ.add(self.STS.multiply(BigDecimal.valueOf(5.5).divide(self.ZAHL100))).setScale(0, BigDecimal.ROUND_DOWN)
                if self.SOLZLZZ.compareTo(BigDecimal.ZERO) == -1:
                    self.SOLZLZZ = BigDecimal.ZERO
                self.BK = self.BK.add(self.STS)
                if self.BK.compareTo(BigDecimal.ZERO) == -1:
                    self.BK = BigDecimal.ZERO
            self.STS = BigDecimal.ZERO
            self.SOLZS = BigDecimal.ZERO
        else:
            self.MSOLZSTS()
        if self.R > 0:
            self.BKS = self.STS
        else:
            self.BKS = BigDecimal.ZERO

    def MSOLZSTS(self):
        if self.ZKF.compareTo(BigDecimal.ZERO) == 1:
            self.SOLZSZVE= self.ZVE.subtract(self.KFB)
        else:
            self.SOLZSZVE= self.ZVE
        if self.SOLZSZVE.compareTo(BigDecimal.ONE) == -1:
            self.SOLZSZVE= BigDecimal.ZERO
            self.X= BigDecimal.ZERO
        else:
            self.X= self.SOLZSZVE.divide(BigDecimal.valueOf(self.KZTAB), 0, BigDecimal.ROUND_DOWN)
        if self.STKL < 5:
            self.UPTAB26()
        else:
            self.MST5_6()
        self.SOLZSBMG= self.ST.multiply(BigDecimal.valueOf(self.f)).setScale(0,BigDecimal.ROUND_DOWN)
        if self.SOLZSBMG.compareTo(self.SOLZFREI) == 1:
            self.SOLZS= self.STS.multiply(BigDecimal.valueOf(5.5)).divide(self.ZAHL100, 0, BigDecimal.ROUND_DOWN)
        else:
            self.SOLZS= BigDecimal.ZERO

    def MOSONST(self):
        self.ZRE4J= (self.JRE4.divide (self.ZAHL100)).setScale (2, BigDecimal.ROUND_DOWN)
        self.ZVBEZJ= (self.JVBEZ.divide (self.ZAHL100)).setScale (2, BigDecimal.ROUND_DOWN)
        self.JLFREIB= self.JFREIB.divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        self.JLHINZU= self.JHINZU.divide (self.ZAHL100, 2, BigDecimal.ROUND_DOWN)
        self.MRE4()
        self.MRE4ABZ()
        self.ZRE4VP = self.ZRE4VP.subtract(self.JRE4ENT.divide(self.ZAHL100))
        self.MZTABFB()
        self.VFRBS1 = ((self.ANP.add(self.FVB.add(self.FVBZ))).multiply(self.ZAHL100)).setScale(2,BigDecimal.ROUND_DOWN)
        self.MLSTJAHR()
        self.WVFRBO = ((self.ZVE.subtract(self.GFB)).multiply(self.ZAHL100)).setScale(2, BigDecimal.ROUND_DOWN)
        if self.WVFRBO.compareTo(BigDecimal.ZERO) == -1 :
            self.WVFRBO = BigDecimal.ZERO
        self.LSTOSO= self.ST.multiply (self.ZAHL100)

    def MRE4SONST(self):
        self.MRE4()
        self.FVB= self.FVBSO
        self.MRE4ABZ()
        self.ZRE4VP = self.ZRE4VP.add(self.MBV.divide(self.ZAHL100)).subtract(self.JRE4ENT.divide(self.ZAHL100)).subtract(self.SONSTENT.divide(self.ZAHL100))
        self.FVBZ= self.FVBZSO
        self.MZTABFB()
        self.VFRBS2 = ((((self.ANP.add(self.FVB).add(self.FVBZ))).multiply(self.ZAHL100))).subtract(self.VFRBS1)

    def UPTAB26(self):
        if self.X.compareTo(self.GFB.add(self.ZAHL1)) == -1:
            self.ST= BigDecimal.ZERO
        else:
            if self.X.compareTo (BigDecimal.valueOf(17800)) == -1:
                self.Y = (self.X.subtract(self.GFB)).divide(self.ZAHL10000, 6,BigDecimal.ROUND_DOWN)
                self.RW= self.Y.multiply (BigDecimal.valueOf(914.51))
                self.RW= self.RW.add (BigDecimal.valueOf(1400))
                self.ST= (self.RW.multiply (self.Y)).setScale (0, BigDecimal.ROUND_DOWN)
            else:
                if self.X.compareTo (BigDecimal.valueOf(69879)) == -1:
                    self.Y= (self.X.subtract (BigDecimal.valueOf(17799))).divide (self.ZAHL10000, 6, BigDecimal.ROUND_DOWN)
                    self.RW= self.Y.multiply (BigDecimal.valueOf(173.1))
                    self.RW= self.RW.add (BigDecimal.valueOf(2397))
                    self.RW= self.RW.multiply (self.Y)
                    self.ST= (self.RW.add (BigDecimal.valueOf(1034.87))).setScale (0, BigDecimal.ROUND_DOWN)
                else:
                    if self.X.compareTo (BigDecimal.valueOf(277826)) == -1:
                        self.ST= ((self.X.multiply (BigDecimal.valueOf(0.42))).subtract (BigDecimal.valueOf(11135.63))).setScale (0, BigDecimal.ROUND_DOWN)
                    else:
                        self.ST= ((self.X.multiply (BigDecimal.valueOf(0.45))).subtract (BigDecimal.valueOf(19470.38))).setScale (0, BigDecimal.ROUND_DOWN)
        self.ST= self.ST.multiply (BigDecimal.valueOf(self.KZTAB))
