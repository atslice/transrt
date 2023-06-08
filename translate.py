import json
import datetime
import copy
import os
import shutil
import re
import argparse

# https://py-googletrans.readthedocs.io/en/latest/
# https://pypi.org/project/googletrans/
# https://github.com/matheuss/google-translate-api
# pip install googletrans
# python3 -m pip install googletrans==3.1.0a0
# for colab: use below
# !pip install googletrans==3.1.0a0
# if you see invalid command 'bdist_wheel', please 'pip install wheel'

from googletrans import Translator
# https://github.com/ssut/py-googletrans/issues/280
# For anyone receives NoneType' object has no attribute 'group, if you are currently using googletrans==3.0.0, 
# please switch to googletrans==3.1.0a0 for the temporary fix.
# Related Issue: #234
# from transcript2srt_cn_whisper import combine_whisper
# from transcript2srt_cn_whisper import to_combine
# from transcript2srt_cn_whisper import to_srt

def parse_args():
    """
        parse arguments
        return: the first argv str if there are any passed arguments; None if no argument is passed
    """
    parser = argparse.ArgumentParser()
    # parser.add_argument("-dt", "--dtbase", type=int, help="filter those dt hours ago")
    # parser.add_argument("-s", "--source", type=str, nargs='+', help="enable the specified source only")  # para nargs='+', form a list for args.source
    #  Note: error: ambiguous option: -mt could match -m, -mtc
    # seems parser uses ambiguous match, -pn could match -pnu
    # parser.add_argument("-l", "--url", action="store_true", help="parse from conf_test/urls.txt")

    parser.add_argument("-s", "--source", type=str, help="specify the json file name") 

    args = parser.parse_args()  
    return args


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):  # consider to judge tzinfo
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)

def dump_json(_file, _dict, sort_keys = False):
    with open(_file, 'w') as fp:
        json.dump(_dict, fp, cls = ComplexEncoder, indent=4, sort_keys=sort_keys)

def transform_time_srt_hour(dot_time):
    """
        "04:36.4" to "00:04:36,400"
    """
    if not '.' in dot_time:  # already standard
        return dot_time
    print('dot_time: %s' % dot_time)
    hm_m = dot_time.split('.')
    hm = hm_m[0]
    if len(hm.split(':')) == 2:
        hm = '00:%s' % hm
    ms = str(int(hm_m[1])*100)
    ms = '000' if (ms == '0') else ms
    # print('%s,%s' %(hm, ms))
    return '%s,%s' %(hm, ms)


def combine(json_transcripts, json_pairs):
    """
    json_transcripts:
        [
            {
                "in": "00:00.4",
                "order": 1,
                "out": "00:00.7",
                "text": "Mr."
            },
            {
                "order": 6,
                "in": "00:00:41,219",
                "out": "00:00:51,060",
                "text": " inequalities. We have seen how algorithmic biases can perpetuate discrimination and prejudice,"
            },            
            ...
        ]
    json_pairs:
        [
            {
                "origin": "Mr.",
                "target": "\u5148\u751f\u3002"
            },
            ...
        ]
    Return: (list, boolean)
        the boolean indicates the pairs is empty
    """
    transcripts = []
    pairs = []
    with open(json_transcripts, 'r') as fp:
        transcripts = json.load(fp)
    if os.path.exists(json_pairs):  # if not translate_list, the paris file does not exists
        with open(json_pairs, 'r') as fp:
            pairs = json.load(fp)
    index = 0
    combines = []
    empty_pairs = (len(pairs) == 0)
    for transcript in transcripts:
        info = copy.deepcopy(transcript)
        origin = transcript['text']
        if not empty_pairs:
            if origin == pairs[index]['origin']:
                info['target'] = pairs[index]['target']
            else:
                print('%d: target not found. origin =%s' %(index, origin))
            index += 1
        combines.append(info)
    return combines, empty_pairs


def break_line(text, chars_limit = 25):
    """
        break text into two lines, bounded to max of chars_limit and a half of the length of text, but comman, prefered first.
        re not perfect yet
        Args: 
            text: str
            chars_limit: int, the max allowed is 70
        Return: str, seperated text by \n
    """
    # be careful of digit 35,000
    len_text = len(text)
    max_chars = max(chars_limit, len_text / 2)
    if len_text <= max_chars:  # not to break
        return text
    # print(len(text))
    digits = re.findall(r'\d+[,\d{3}]+', text)  # find the digit seperated by , not perfect
    # 非常高兴能够全面量产 H100，我要感谢你们所有人的支持 still matches 100
    new_text = text
    for digit in digits:
        new_digit = digit.replace(',', '')
        new_text = new_text.replace(digit, new_digit)  # remove , for digit

    # if you can find a re.split to replace the only non-digit , then you do not need to replace digit
    groups = new_text.split('，')  # ，the Chinese ,
    sum = 0
    text1 = ''
    text2 = ''
    num = len(groups)
    i = 0
    for group in groups:
        i += 1
        sum = sum + len(group) + 1  # count the length of text
        if sum < max_chars:
            text1 += group
            text1 = text1 + '，' if i < num else text1
        else:
            if i == 1: # the first group which has been greater than the limit
                text1 = group + '，' if num > 1 else group
            else:
                text2 += group
                text2 = text2 + '，' if i < num else text2
    result = text1 if text2 == '' else '%s\n%s' %(text1, text2)
    return result


def write_srt2(file_name, _dict, order = 'order', start = 'in', end = 'out', text = 'text', text_second = None):
    """
        write srt file    
        Args:
            _dict: list of dict
            order: str, the key to read the order for srt
            start: str, the key to read the start time
            end: str, the key to read the end time            
            text: str, the key to read the text
            text_second: str, usually the key to read cn text
    """
    with open(file_name, 'w', encoding='utf-8') as writer:
        pass  
    for transcript in _dict:
        order_int = transcript[order]
        in_time = transcript[start]
        out_time = transcript[end]
        subtitle = transcript[text].strip(' ')
        start_time = transform_time_srt_hour(in_time)
        end_time = transform_time_srt_hour(out_time)
        time_line = '%s --> %s' %(start_time, end_time)
        with open(file_name, 'a', encoding='utf-8') as writer:
            if text_second is None:
                script = '%s\r\n%s\r\n%s\r\n\r\n' %(str(order_int), time_line, subtitle)
            else:
                subtitle2 = transcript[text_second].strip(' ')
                subtitle2 = break_line(subtitle2, chars_limit=25)
                script = '%s\r\n%s\r\n%s\r\n%s\r\n\r\n' %(str(order_int), time_line, subtitle, subtitle2)
            writer.write(script)


def judge_sentence(text):
    """
        count how many specified chars appear in the text
        return int
    """
    c = 0
    for char in text:
        if char in ('？', '。'):
            c += 1
    return c


def judge_sentence_en(text):
    """
        Args:
            text: str, should be English str and punctation
        count how many specified chars appear in the text
        return int
    """
    c = 0
    new_text = text.replace('Mr.', 'Mr').replace('U.S.', 'US').replace('US.', 'US').replace('Dr.', 'Dr').replace('A.I.', 'AI')
    for char in new_text:
        if char in ('?', '.'):  # should exclude 88.6%
            c += 1
    digits_dot = len(re.findall(re.compile(r'[\d]+\.[\d]+'), new_text))  # count the digits with dot
    c -= digits_dot  # should also exclude domain name
    c = max(c, 0)
    return c

def judge_sentence_en_2(text):
    """
        Args:
            text: str, should be English str and punctation
        count how many specified chars appear in the text
        return int
    """
    c = 0
    new_text = text.replace('Mr.', 'Mr').replace('U.S.', 'US').replace('US.', 'US').replace('Dr.', 'Dr').replace('A.I.', 'AI').replace('St.', 'St')
    for char in new_text:
        if char in ('?'):  # 
            c += 1
    ignore = len(re.findall(re.compile(r'\.\.\.'), new_text))  # count the ...
    new_text = re.sub(re.compile(r'\.\.\.'), '', new_text)  # to avoid duplicated counting dot at the end of a line, or dot followed by space
    space_dot = len(re.findall(re.compile(r'\. +'), new_text))  # count the dot followed by space
    # "Howard K. Smith"  if you count the pattern "space after dot" as an end of sentence, you have to exclude many midle name followed by dot
    en_name = len(re.findall(re.compile(r'[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+'), new_text))  # count the English midle name, for example: Howard K. Smith, 
    # start with one Upper case letter, then lower case letters and space, then one Uper case letter, then dot and space, Upper case letter, lowercase letters
    return_dot = len(re.findall(re.compile(r'\.$'), new_text))    # count the dot at then end of a line
    sup = len(re.findall(re.compile(r'!'), new_text))    # count the !
    
    c += space_dot + return_dot + sup + ignore - en_name
    return c


def seconds_to_srt(seconds):
    """
        Args:
            seconds: float
        Return: str
    """
    sec = int(seconds)
    ms = int((seconds - sec) * 1000)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    pattern = r'%02d:%02d:%02d,%03d'
    if d > 0:
        h += d * 24
    return pattern % (h, m, s, ms)


def standardize_whisper(json_whisper):
    """
        transform into list

        Args:
            json_whisper: str, path, the path to the Google Colab Whisper exported json, parsed into list of dict as example  

            parsed dict from json_whisper:
        {
            "text": "full_text"
            "segments": [
                {
                    "id": 0,  # id start with 0, different with srt order starting from 1
                    "seek": 0,
                    "start": 0.0,
                    "end": 7.6000000000000005,
                    "text": " is on the oversight of artificial intelligence, the first in a series of hearings intended",
                    "tokens": [50363, 318,...]
                    "temperature": 0.0,
                    "avg_logprob": -0.12471929429069398,
                    "compression_ratio": 1.5141242937853108,
                    "no_speech_prob": 0.012947200797498226            
                },
                ...
            ]
            "language": "en"
        }

        Return:
            list
                [
                    {
                        'order': int,
                        'in': str,  # in srt format  hour:minute:seconds,mill-seconds
                        'out': int,   # in srt format  hour:minute:seconds,mill-seconds
                        'texts': str  # in English
                    },
                    ...
                ]

    """
    with open(json_whisper, 'r') as fp:
        transcripts = json.load(fp)

    return [
            {
                'order': transcript['id'] + 1,
                'in': seconds_to_srt(seconds = transcript['start']),
                'out': seconds_to_srt(seconds = transcript['end']),
                'text': transcript['text']
            }
            for transcript in transcripts["segments"]       
        ]


def transform_whisper(json_whisper, chars_limit = 5000):
    """
        Group text by chars_limit, return a list of group info
        json_whisper:
        {
            "text": "full_text"
            "segments": [
                {
                    "id": 0,  # id start with 0, different with srt order starting from 1
                    "seek": 0,
                    "start": 0.0,
                    "end": 7.6000000000000005,
                    "text": " is on the oversight of artificial intelligence, the first in a series of hearings intended",
                    "tokens": [50363, 318,...]
                    "temperature": 0.0,
                    "avg_logprob": -0.12471929429069398,
                    "compression_ratio": 1.5141242937853108,
                    "no_speech_prob": 0.012947200797498226            
                },
                ...
            ]
            "language": "en"
        }
        Args:
            json_colab: str, path, the path to the Google Colab Whisper exported json, parsed into list of dict as example
        Return:
            list
                [{
                    'chars': int,
                    'number': int,
                    'end_order': int,   # the last order in srt
                    'texts': list of str,
                    'text_joined': str
                },...]
    """

    transcripts = []
    with open(json_whisper, 'r') as fp:
        transcripts = json.load(fp)

    # translator = Translator()
    # chars_limit = 300
    texts = []  # list of dict
    to_trans = [] # list of str
    added = False
    tmp_text = ''
    all_text = ''
    end_order = 0
    if True:
        for transcript in transcripts["segments"]:         
            order = transcript['id'] + 1
            in_time = transcript['start']
            out_time = transcript['end']
            text = transcript['text']
            # print('%d: %s - %s: %s' %(order, in_time, out_time, text))
            all_text += text
            current_length = len(tmp_text)
            tmp_text += text + ' '
            after_length = len(tmp_text)
            # print('%d: length = %d' %(order, len(tmp_text)))
            if after_length > chars_limit:
                end_order += len(to_trans)
                info = {
                    'chars': current_length,
                    'number': len(to_trans),
                    'end_order': end_order,
                    'texts': to_trans,
                    'text_joined': ' '.join(to_trans)
                }            
                texts.append(info)
                added = True                
                to_trans = []  # initialized
                to_trans.append(text)
                tmp_text = ''
                tmp_text += text
            else:
                added = False
                to_trans.append(text)
        # print('len(text) = %d' % len(texts))
        if not added:
            end_order += len(to_trans)
            info = {
                    'chars': after_length,
                    'number': len(to_trans),
                    'end_order': end_order,
                    'texts': to_trans,
                    'text_joined': ' '.join(to_trans)
                }            
            texts.append(info)
            # print('len(text) = %d' % len(texts))
    # check
    texts_len = 0
    for info in texts:
        info_len = info['chars']
        texts_len += info_len
    print('transform_whisper: original length = %d' % len(all_text))
    print('transform_whisper: after group length = %d' % texts_len)
    return texts
        

def translate(infos, trans_list = False):
    """
        Args:
            infos: list, 
                [{
                    'chars': int,
                    'number': int,
                    'end_order': int,
                    'texts': list of str,
                    'text_joined': str
                },...]
            translate_list: boolen, defautl False, whether to translate the texts list
        Return: (list, list)
            The first list:
                [{
                    'chars': int,
                    'number': int,
                    'end_order': int,
                    'texts': list of str,
                    'text_joined': str,
                    'translated': list of str,  # the translated results for texts list
                    'joined_translated': str   # the translated result for text_joined
                },...]
            The second list: pairs
    """

    def translate_list(translator, info):
        """"
            pass list of str to translator, and return a list of translated text
            Args:
                translator: Translator() obj instance
                info: dict
            Return: (list, list)
                the second list is pairs
        """
        translated = []
        pairs = []
        # translate list of str
        origin_texts = info['texts']
        
        translations = translator.translate(origin_texts, dest = 'zh-cn', src = 'en')
        trans = []
        trans_hash = {}
        # print(translations)  # [<googletrans.models.Translated object at 0x7f82dc17d160>, <googletrans.models.Translated object at 0x7f82dc138198>,...]
        
        for translation in translations:  # if passed parameter is not list: TypeError: 'Translated' object is not iterable
            origin = translation.origin
            target = translation.text
            trans_info = {
                'origin': origin,
                'target': target
            }
            # print(origin)
            print(target)
            trans.append(trans_info)
            pairs.append(trans_info)
            trans_hash[origin] = target
            
        new_info['trans_pairs'] = trans   # list of dict, pairs
        translated = [
            trans_hash[origin]
            for origin in origin_texts
        ]
        return translated, pairs      

    translator = Translator()
    new_infos = []
    pairs = []
    i = 0
    for info in infos:
        i += 1
        new_info = copy.deepcopy(info)

        # translate joined str
        print('translating %d: chars = %d' %(i, info['chars']))
        text_joined = info['text_joined']
        translation = translator.translate(text_joined, proxies={'http://': 'http://127.0.0.1:10809', 'https://': 'http://127.0.0.1:10809'}, dest = 'zh-cn', src = 'en')
        target = translation.text
        new_info['joined_translated'] = target  # str

        if trans_list:
            new_info['translated'], pairs = translate_list(translator=translator, info=info)   # list of str

        new_infos.append(new_info)
    return new_infos, pairs


def to_combine(json_transcripts, json_pairs):
    """
        Args:
            json_transcripts: str, path to input json
            json_pairs: str, path to json pairs
    """
    out_dir = 'translated'
    if not os.path.exists(out_dir):
        os.mkdir(out_dir) 
    # combine translated transcripts with the original one
    # json_pairs = os.path.join(out_dir, 'translated_pairs.json')
    combines, empty_pairs = combine(json_transcripts = json_transcripts, json_pairs = json_pairs)

    # dump to file
    json_combine = os.path.join(out_dir, 'combines_translated.json')
    dump_json(_file = json_combine, _dict = combines)
    return combines, empty_pairs 


def to_srt(translated, combines, empty_pairs = True, name = 'sentences_en_cn'):
    """
        Args:
            json_translated: list
                [{
                    'chars': int,
                    'number': int,
                    'end_order': int,
                    'texts': list of str,
                    'text_joined': str,
                    'translated': list of str,  # the translated results for texts list
                    'joined_translated': str   # the translated result for text_joined
                },...]        
            combines:  list
            empty_pairs: boolean, if the pairs list is empty, it is true
            name: str, will be used as the filename of the translated en_cn srt file, txt_en_cn
    """
    out_dir = 'translated'
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)    
    # combines = to_combine()

    # write to srt files

    srt_origin = os.path.join(out_dir, 'transcripts_en.srt')
    srt_cn = os.path.join(out_dir, 'transcripts_cn.srt')
    srt_en_cn = os.path.join(out_dir, 'transcripts_en_cn.srt')
    write_srt2(file_name = srt_origin, _dict = combines, order = 'order', start = 'in', end = 'out', text = 'text')
    if not empty_pairs:
        write_srt2(file_name = srt_cn, _dict = combines, order = 'order', start = 'in', end = 'out', text = 'target')
        write_srt2(file_name = srt_en_cn, _dict = combines, order = 'order', start = 'in', end = 'out', text = 'text', text_second = 'target')                     

    txt_en_cn = os.path.join(out_dir, '%s_text_en_cn.txt' % name)
    with open(txt_en_cn, 'w', encoding='utf-8') as writer:
        pass    
    # json_translated = os.path.join(out_dir, 'translated.json')
    # transcripts = []
    # with open(json_translated, 'r') as fp:
    #    transcripts = json.load(fp)
    transcripts = translated       
    with open(txt_en_cn, 'a', encoding='utf-8') as writer:
        for transcript in transcripts:
            chars = transcript['chars']
            end_order = transcript['end_order']
            text_joined = transcript['text_joined']
            joined_translated = transcript['joined_translated']
            writer.writelines('chars: %d\r\n' % chars)
            writer.writelines('end_order: %d\r\n' % end_order)
            text_joined_new = text_joined.replace('. ', '.\r\n').replace('? ', '?\r\n')
            writer.writelines(text_joined_new)
            writer.writelines('\r\n\r\n')
            joined_translated_new = joined_translated.replace('。', '。\r\n').replace('？', '？\r\n')
            writer.writelines(joined_translated_new)
            writer.writelines('\r\n\r\n')

    # Try to break Chinese sentences

    
    joined_translateds = [
        transcript['joined_translated']
        for transcript in transcripts
    ]
    joined_translated_all = ' '.join(joined_translateds)  # the full translated text
    joined_translated_all_tmp = joined_translated_all.replace('。', '。\n').replace('？', '？\n').replace('……', '……\n').replace('！', '！\n').replace('......', '......\n') # ......  # the Chinese …… maps English ...
    joined_translated_list = joined_translated_all_tmp.split('\n')  # split into sentences list, # the last one is empty,  the result for 'what\n'.split('\n') is ['waht', '']
    if joined_translated_list[-1] == '':
        joined_translated_list = joined_translated_list[:-1]

    len_joined = len(joined_translated_list)
    print('joined translated sentences = %d' % len(joined_translated_list))  
    
    txt_joined_translated = os.path.join(out_dir, 'translated.txt')
    with open(txt_joined_translated, 'w') as writer:
        ct = 0
        for text in joined_translated_list:
            ct += 1
            writer.writelines('%d: %s\r\n' %(ct, text))

    len_combines = len(combines) # the number of lines in original whisper srt
    # normally len(joined_translated_list) is smaller than/equal to/greater than len(combines)
    new_combines = []
    i = 0
    c = 0
    cc= 0
    all_processed = True
    logged = False
    for transcript in combines:     
        # print('%s - %s: %s' %(transcript['in'], transcript['out'], transcript['text']))
        # order = transcript['order']
        # print(order)
        c += 1
        new_transcript = copy.deepcopy(transcript)
        
        # judge how many sentence
        #text = transcript['target']
        text = transcript['text']
        counts = judge_sentence_en_2(text)
        cc += counts
        # print('loop c = %d: joined translated index i / len = %d / %d, accumulated judge sentence cc = %d, current line count = %d' %(c, i, len_joined, cc, counts))
        if i > len_joined - 1:
            all_processed = False
            if not logged:
                logged = True
                logs = 'processed / original whisper srt = %d / %d' % (c - 1, len_combines)
            continue  # temporary solution; to continue to static sentences en, not break
        if counts == 0:
            new_transcript['cn_subtitle'] = joined_translated_list[i]
        else:
            cn_subtitle = ''
            for j in range(counts):
                if i > len_joined - 1:
                    all_processed = False
                    logs_j = 'out of index while adding up sentences. i = %d' % i
                    logs = 'processed / original whisper srt = %d / %d' % (c - 1, len_combines)
                    print(logs_j)
                    break
                if cn_subtitle == '':
                    cn_subtitle = joined_translated_list[i]
                else:
                    cn_subtitle = '\r\n'.join([cn_subtitle, joined_translated_list[i]])
                i += 1
            new_transcript['cn_subtitle'] = cn_subtitle        
        new_combines.append(new_transcript)
    print('accumulated judged sentences en = %d' % cc)
    if all_processed:
        print('all processed.')
    else:
        print(logs)
    json_new_combine = os.path.join(out_dir, 'sentences_translated.json')
    dump_json(_file = json_new_combine, _dict = new_combines)
  
    srt_cn_sentences = os.path.join(out_dir, 'sentences_cn.srt')
    filename = '%s.srt' % name
    srt_en_cn_sentences = os.path.join(out_dir, filename)
    write_srt2(file_name = srt_cn_sentences, _dict = new_combines, order = 'order', start = 'in', end = 'out', text = 'cn_subtitle')
    write_srt2(file_name = srt_en_cn_sentences, _dict = new_combines, order = 'order', start = 'in', end = 'out', text = 'text', text_second = 'cn_subtitle')


def main():
    # group list of transcripts

    in_dir = ''

    args = parse_args()
    json_arg = args.source
    json_default =  os.path.join(in_dir, 'whisper.json')
    json_file = None
    if not json_arg is None:
        if not os.path.exists(json_arg):
            print('File not existed: %s' % json_arg)
            return
        basename = os.path.basename(json_arg)
        extension = re.findall(r'\.\w+$', basename)
        print('Uploaded file extention is: %s' % extension)
        json_file = re.sub(r'\.\w+$', '.json', json_arg)
        print('whisper json should be: %s' % json_file)
    json_whisper = json_default if json_file is None else json_file
    if not os.path.exists(json_whisper):
        print('input json file not found: %s' % json_whisper)
        return
    
    basename = os.path.basename(json_whisper)
    # extension = re.findall(r'\.\w+$', basename)
    nameonly = re.sub(r'\.\w+$', '', basename)  # remove .m4a from xxx.f140.m4a
    json_whisper_fmt = os.path.join(in_dir, '%s_fmt.json' % nameonly)
    with open(json_whisper, 'r') as fp:
        whisper_dict = json.load(fp)
    dump_json(_file = json_whisper_fmt, _dict = whisper_dict)    # just format the whisper output for further manually check    
    nameonly = re.sub(r'\.\w+$', '', nameonly)  # the nameonly will be used as output srt filename. remove .f140 from  xxx.f140

    out_dir = 'translated'
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    whispers = standardize_whisper(json_whisper = json_whisper)   

    # json_whisper_std is the standardized original source which is used to combine translated transcripts
    json_whisper_std = os.path.join(out_dir, 'whisper_std.json')
    dump_json(_file = json_whisper_std, _dict = whispers)

    infos = transform_whisper(json_whisper=json_whisper, chars_limit = 10000)
    json_transfrom = os.path.join(out_dir, 'transform.json')
    dump_json(_file = json_transfrom, _dict = infos)

    # google translate
    # for the broken sentences in original source, the translated sentences are not accurated and usually meaningless, so it is no need to trans_list
    # we will prefer joining original texts and then spliting the translated texts to match the original ones
    new_infos, pairs = translate(infos)  # trans_list default False, and pairs will be returned empty
    json_pairs = os.path.join(out_dir, 'translated_pairs.json')
    json_translated = os.path.join(out_dir, '%s_translated.json' % nameonly)
    dump_json(_file = json_translated, _dict = new_infos)
    if len(pairs) > 0:
        dump_json(_file = json_pairs, _dict = pairs)

    # combine translated transcripts with the original ones
    combines, empty_pairs = to_combine(json_transcripts = json_whisper_std, json_pairs = json_pairs)   # return (list, boolean)
    # write to srt files
    to_srt(translated = new_infos, combines = combines, empty_pairs = empty_pairs, name = nameonly)
    # copy os.path.join(out_dir, '%s.srt' % nameonly) to current directory
    trans_srt = os.path.join(out_dir, '%s.srt' % nameonly)
    if os.path.exists(trans_srt):
        try:
            shutil.copy(trans_srt, '.')
        except BaseException as e:
            print('Fail to copy %s, error = %s' %(trans_srt, format(e)))

    
if __name__ == "__main__":
    main()