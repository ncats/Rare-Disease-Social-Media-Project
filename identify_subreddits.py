#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maps GARD rare diseases to subreddit forums using modified form of NormMap using spaCy.
"""

from os.path import join
import time
import spacy
from utils.utils import dump_json, load_json
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc

class MapSubreddit:
    """
    A class to map the GARD rare diseases to subreddit forums.

    Mapping Algorithm:
    1. Create phrases from GARD data based on names and synonyms for use in the PhraseMatcher.
    2. Use preprocessed and normalized text data of descriptions (short and public) of subreddits
       to match against the patterns in the PhraseMatcher.

    :param path: Path for storing the file of subreddit data.
    :type path: str.

    :param nlp: Spacy pipeline to load.
    :type nlp: spacy pipeline.

    :param attr: Attribute to set Phrasematcher to. Default is LOWER to have matches be case
                 insensitive.
    :type attr: str.
    """

    def __init__(self, nlp = spacy.load('en_core_web_lg'), attr='LOWER', path='../data'):
        self.path = path
        self.nlp = nlp
        self.matcher = PhraseMatcher(self.nlp.vocab, attr=attr)
        self.data = load_json(join(self.path,'preprocessed_subreddit_list.json'))
        self._get_gard_data()
        self._convert_data()
        self._use_phrasematcher()

    def _get_gard_data(self):
        """
        Loads the JSON GARD data.
        """
        path = join(self.path,'neo4j_rare_disease_list.json')
        gard_data = load_json(path)
        self._create_gard_data(gard_data)

    def _create_gard_data(self,data):
        """
        Creates dictionary for matching name and synonym from GARD rare diseases.

        :param data: JSON of GARD rare disease query results.
        :type data: JSON.
        """
        names = [disease['Name'] for disease in data]
        synonyms = []
        for disease in data:
            if disease['Synonyms']:
                for synonym in disease['Synonyms']:
                    synonyms.append(synonym)

        # Removing synonyms that have a large frequency of false positives and no to very low
        # number of true positives.
        synonyms = [synonym for synonym in synonyms if synonym not in ['ChILD','Tina','Azul']]
        # Removing synonyms that are acronyms only. Too many false positives from them.
        synonym_patterns = [self.nlp.make_doc(synonym) for synonym in synonyms
                           if not synonym.isupper()]

        # Removing non-unique synonyms.
        synonym_patterns = list(set(synonym_patterns))
        self.matcher.add('Synonyms', synonym_patterns)

        name_patterns = [self.nlp.make_doc(name) for name in names]
        self.matcher.add('Names', name_patterns)

    def _convert_disease_string(self,text):
        """
        Converts list of names and synonyms to one string for processing.

        :param text: List of strings.
        :type text: list.

        :return: String of names and synonyms.
        """
        return ' '.join(text)

    def _convert_data(self):
        """
        Converts the JSON data into list of tuples for the form: [(doc, context)].
        This is for ingestion into nlp.pipe for processing.
        """
        self.data = [(text, context) for text, context in self.data]

    def _use_phrasematcher(self):
        """
        Uses the PhraseMatcher on each subreddit to match patterns from GARD data on rare disease
        names and synonyms to description text of subreddit. Once finished, it calls function to
        print the results.
        """
        # Register the Doc extension metadata tags (default None). These are mostly for testing and
        # debugging purposes at the moment.
        Doc.set_extension('name', default = None)
        Doc.set_extension('title', default = None)
        Doc.set_extension('subscribers', default = None)
        Doc.set_extension('created_utc', default = None)
        total_count = 0
        max_length = len(self.data)
        matches = {}
        print('Processing text ...')
        t0 = time.time()
        # Use of pipe greatly speeds up processing of the data.
        for doc, context in self.nlp.pipe(self.data, as_tuples=True):
            # Set metadata attributes from the context.
            doc._.name = context['name']
            doc._.title = context['title']
            doc._.subscribers = context['subscribers']
            doc._.created_utc = context['created_utc']
            total_count += 1
            if total_count % 1000 == 0:
                t = round(time.time() - t0, 1)
                print(f'---Progress: {total_count}/{max_length} Subreddit: {doc._.name} Time: {t}')
            for match_id, start, end in self.matcher(doc):
                pattern_type = self.nlp.vocab.strings[match_id]
                matches[doc._.name] = matches.get(doc._.name, []) + [(pattern_type, str(doc[start:end]))]
                print(f'Subreddit: {doc._.name} Match: {pattern_type, doc[start:end]} \
                        Subreddits Processed: {len(matches)}/{total_count}')
        dump_json(self.path, matches,'normalized_subreddit_matches.json')

class MapResults:
    def __init__(self, false_positives, path='..\data'):
        self.path = path
        self.false_positives = false_positives
        self.matches = self._get_matches()
        self.true_positives = self._get_true_positives()

        self.gard_data = load_json(join(self.path,'neo4j_rare_disease_list.json'))
        self.reddit_data = load_json(join(self.path,'preprocessed_subreddit_list.json'))

        self.rare_disease_dict = {}
        self._find_matches()
        dump_json(self.path, self.rare_disease_dict, 'subreddit_GARD_matches.json')

    def _get_matches(self):
        return load_json(join(self.path,'normalized_subreddit_matches.json'))

    def _get_true_positives(self):
        return {key:value for key, value in self.matches.items()
                if key not in self.false_positives}

    def _find_match(self,hit_list):
        hit_type = hit_list[0]
        hit_text = hit_list[1].lower()

        match_dict = {}
        if hit_type == 'Names':
            for index in self.gard_data:
                if hit_text in index['Name'].lower():
                    match_dict[index['GARD id']] = index['Name']
        if hit_type == 'Synonyms':
            for index in self.gard_data:
                if index['Synonyms']:
                    for synonym in index['Synonyms']:
                        if hit_text == synonym.lower():
                            match_dict[index['GARD id']] = index['Name']
        return match_dict

    def _find_matches(self):
        for subreddit, hits in self.true_positives.items():
            search_term_list = [(hit[0], hit[1]) for hit in hits]
            search_term_list = list(set(search_term_list))
            gard_id_list = []
            gard_name_list = []
            for search_term in search_term_list:
                match_dict = self._find_match(search_term)
                gard_id_list.extend(list(match_dict.keys()))
                gard_name_list.extend(list(match_dict.values()))
            gard_id_list = list(set(gard_id_list))
            gard_name_list = list(set(gard_name_list))
            text, title, subscribers, created_utc = self._get_subreddit_data(subreddit)
            self.rare_disease_dict[subreddit] = {'GARD Names': gard_name_list,
                                                'GARD ids': gard_id_list,
                                                'title': title,
                                                'subscribers': subscribers,
                                                'created_utc': created_utc,
                                                'text': text
                                                }

    def _get_subreddit_data(self,subreddit):
        data = [(text, context) for text, context in self.reddit_data
                if context['name'] == subreddit]
        data = data[0]
        text = data[0]
        title = data[1]['title']
        subscribers = data[1]['subscribers']
        created_utc = data[1]['created_utc']
        return text, title, subscribers, created_utc


def main():
    """
    Calls class
    """
    t0 = time.time()
    MapSubreddit()
    t = round(time.time() - t0, 1)
    print(f'Time elapsed for converting subreddit was {t} seconds.')

    false_positives = ['baltimore', 'stocks', 'ACDC', 'polydactyl', 'Asian_Fever','JRPG', 'Lemon',
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
    t0 = time.time()
    MapResults(false_positives=false_positives)
    t = round(time.time() - t0, 1)
    print(f'Time elapsed for matching GARD ids to subreddit hits was {t} seconds.')
if __name__ == '__main__':
    main()
