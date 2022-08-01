class Blacklist ():
    def __init__(self):
        self.false_positives_acronyms = ['ChILD','Tina','Azul']
        self.false_positives = ['baltimore', 'stocks', 'ACDC', 'polydactyl', 'Asian_Fever','JRPG', 'Lemon',
                       'lebanon', 'Iditarod', 'bigfoot', 'Pantera', 'CharterCities', 'thrashmetal',
                       'Asthma', 'beadsprites', 'Chameleons', 'metaphorically', 'MovieExchange',
                       'Hell_On_Wheels', 'MicroPenis', 'RoomofRequirement', 'Basenji',
                       'machinehead', 'randomactsofsteam', 'famitracker', 'lilypond', 'GeddyLee',
                       'Eddsworld', 'deathbombarc', 'umineko','hyperlexia', 'higurashi',
                       'Sepultura', 'Anthrax', 'DeepPurple', 'osutickets', 'piratetalk',
                       'Higurashinonakakoroni','naturalbodybuilding', 'Peptides', 'Flume', 'Hausa',
                       'mondaiji', 'Microbiome', 'Listener', 'serene', 'thumbcats',
                       'Hitomi_Tanaka', 'Unity2D', 'EAF','swifties', 'WhatSoNot', 'dogeforgames',
                       'gridcoin', 'dudewheresmybank', 'VaccineMyths','PVcommission', 'anabolic',
                       'RomanAtwood', 'Vulfpeck', 'MedPeds', 'AdverseEffects',
                       'HailTheSun','Dutch_Bros', 'stilltrying', 'AltMicrobiology',
                       'AnkylosingSpondilitis', 'magicTCGmemes', 'dtgprinting', 'PEDs',
                       'HarshlyCritical', 'Urinalysis', 'DiamondDynasty', 'PakCricket',
                       'AnthersLadder', 'darkserenesingle', 'NomaReservations',
                       'DihydrogenMonoxide', 'UminekoNoNakuKoroNi', 'amazonprimeday',
                       'discordservers', 'Breatharianism', 'CaptainHair59', 'TheHealthyOnes',
                       'healthinspector', 'Soulfly', 'F2Pironman', 'loperamide',
                       'TheAdamWarrenFanClub', 'sarmsourcetalk', 'AllMicrobiology', 'yiffcaptions',
                       'Biohacked', 'NickMurphy', 'sasukebukkake', 'ParahumansPlace',
                       'sportscontests', 'picu', 'SleepyMemes','HIprepared', 'TaronEgerton',
                       'PEDsR', 'MacromastiaFiction','RDRInteractiveSeason', 'Plumpandnaturaltits',
                       'BlockchainBanknTrust', 'BlankMind', 'HoldMyTetanusShot', 'CH_Kitties',
                       'Bubonicmemes', 'EnoughWumaoSpam', 'ASTERISM_Rules', 'BlueDragonfly',
                       'measlesrightsmovement', 'JeremyCorbell', 'AltitudeSickness','FuckTyphus',
                       'duckxrec', 'MacromastiaTits', 'lyssaabbby', 'NomaGuideFermentation',
                       'UniqueBodies', 'Macromastiafactory', 'HiLariBakNEW', 'China_Flu',
                       'MassMove', 'CoronavirusConspiracy', 'Wuhan_Flu', 'UnexpectedCoronavirus',
                       'rabiesbabies', 'COVID19', '2019COVID', 'PandemicPreps', 'CoronavirusUS',
                       'Coronavirus_COVID_19', 'CoronavirusAustralia', 'CovidMapping',
                       'Coronavirus_BC', 'coronavirusflorida', 'Koronawirus', 'CoronavirusFrance',
                       'COVID19_Arkansas', 'CoronaUSA', 'CoronaVirusWV', 'SARS_CoV2',
                       'CoronavirusAlabama', 'CoronavirusColorado', 'CoronavirusAZ',
                       'CoronavirusEU', 'CoronavirusUT', 'CanadaCoronavirus', 'CoronavirusWA',
                       'TexasCoronavirus', 'CoronavirusSeattle', 'coronavirusNYC',
                       'CoronavirusVIC', 'CoronavirusAtlanta', 'IndiaCoronavirus',
                       'Coronavirusworld', 'Covid19_Ohio', 'CoronavirusNebraska',
                       'CoronaVirusNepal', 'CoronaMENA', 'Coronavirus_PH', 'Coronavirus_KY',
                       'coronavirusKY', 'COVID19NYC', 'CoronavirusCleveland',
                       'CoronaVirusMontreal', 'coronaviruspensacola', 'BeardsAndFeet',
                       'CoronaIndia', 'Quarantainment', 'covid19stack', 'coronaslovakia',
                       'CoronavirusData', 'coronavaccine', 'CoronavirusRecession', 'Antilockdown',
                       'COVID19_data', 'Coronavirusdepression', 'Covid19Symptoms', 'RealFDRhate',
                       'coronalosangeles', 'Coronavirus_AFRICA', 'Antipandemic', 'coronanorge',
                       'SarsCovTwo', 'spungbo', 'Prolockdown', 'DRACOMemes', 'PandemicGirls',
                       'Coxville', 'MycoRhizo', 'INFOCoronavirus', 'BabyPowder',
                       'KAssadpahakbsknsmje', 'VitaminD3', 'VitaminCBenefits', 'GinkgoBiloba',
                       'UncensoredPEDs', 'MacPintaFanClub','kidsforkarma', 'SARSCOVID2',
                       'MEDCOVID19', 'GauchoPeopleTwitter', 'BlackMarketOilPen', 'the_rona',
                       'CANCEROUSCHRISTIAN', 'AmazingAyheistMicropp', 'ibroadcast','CDH1',
                       'Naegleriafowleri', 'PNESWARRIORS', 'E_L', 'CoronavirusFood',
                       'fuckswampfever', 'Kaolin']
                    
    def _clear(self, acronyms=False):
        if acronyms:
            self.false_positives_acronyms = list()
             
        else:
            self.false_positives = list()
            
    def _getall(self, acronyms=False):
        if acronyms:
            return self.false_positives_acronyms 
        else:
            return self.false_positives

    def _remove(self, word, acronyms=False):
        if acronyms:
            self.false_positives_acronyms.remove(word)
        else:
            self.false_positives.remove(word)

    def _pop(self, index, acronyms=False):
        if acronyms:
            self.false_positives_acronyms.pop(index)
        else:
            self.false_positives.pop(index)

    def _add(self, word, acronyms=False):
        if acronyms:
            self.false_positives_acronyms.append(word)
        else:
            self.false_positives.append(word)