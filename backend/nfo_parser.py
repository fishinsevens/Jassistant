# backend/nfo_parser.py
import xml.etree.ElementTree as ET
import json
import logging
import re
import os
from collections import defaultdict

logger = logging.getLogger(__name__)

# 用于支持CDATA的处理
class CDATA(str):
    pass

def etree_to_dict(t):
    """将ET元素转换为字典，保留CDATA信息"""
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

def parse_nfo_file(nfo_path):
    try:
        if not os.path.exists(nfo_path):
            logger.warning(f"NFO文件不存在: {nfo_path}")
            return None
            
        if not os.path.isfile(nfo_path):
            logger.warning(f"路径不是文件: {nfo_path}")
            return None
        
        # 检查文件权限
        if not os.access(nfo_path, os.R_OK):
            logger.warning(f"无法读取NFO文件 (权限问题): {nfo_path}")
            return None
            
        # 读取原始文件内容以检测CDATA段
        try:
            with open(nfo_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"读取NFO文件内容失败: {nfo_path} - {e}")
            return None
        
        # 检查是否是空文件
        if not content.strip():
            logger.warning(f"NFO文件为空: {nfo_path}")
            return None
        
        try:
            tree = ET.parse(nfo_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.warning(f"XML解析错误: {nfo_path} - {e}")
            return None
    except (FileNotFoundError, ET.ParseError) as e:
        logger.warning(f"无法读取或解析NFO文件: {nfo_path} - {e}")
        return None
    except Exception as e:
        logger.error(f"处理NFO文件时发生意外错误: {nfo_path} - {e}")
        return None
        
    data = {}
    # 保存原始文件路径，而不是XML对象
    data['_nfo_path'] = nfo_path
    
    # 增加需要保留的字段
    single_fields = ['title', 'originaltitle', 'sorttitle', 'plot', 'originalplot', 'outline', 
                     'tagline', 'releasedate', 'year', 'studio', 'label', 'rating', 
                     'criticrating', 'num', 'countrycode', 'customrating', 'mpaa', 
                     'cover', 'runtime', 'website']
    for field in single_fields:
        element = root.find(field)
        if element is not None and element.text:
            # 检查是否有CDATA包裹
            if field in content and f'<![CDATA[' in content:
                try:
                    cdata_pattern = rf'<{field}><!\[CDATA\[(.*?)\]\]></{field}>'
                    cdata_match = re.search(cdata_pattern, content, re.DOTALL)
                    if cdata_match:
                        data[field] = cdata_match.group(1).strip()
                        continue
                except Exception as e:
                    logger.warning(f"CDATA提取失败: {field} - {e}")
            
            data[field] = element.text.strip()
            
    multi_fields = {'sets': 'set', 'actors': 'actor', 'genres': 'genre', 'tags': 'tag'}
    for data_key, xml_tag in multi_fields.items():
        try:
            elements = root.findall(xml_tag)
            if xml_tag == 'actor':
                values = [actor.findtext('name', default='').strip() or actor.text.strip() if actor.text else '' 
                         for actor in elements if (actor.findtext('name', default='').strip() or (actor.text and actor.text.strip()))]
            elif xml_tag == 'set':
                values = [s.findtext('name', default='').strip() or s.text.strip() if s.text else '' 
                         for s in elements if (s.findtext('name', default='').strip() or (s.text and s.text.strip()))]
            else:
                values = [elem.text.strip() for elem in elements if elem.text and elem.text.strip()]
            
            # 过滤空值
            values = [v for v in values if v]
            
            if values:
                data[data_key] = values
        except Exception as e:
            logger.warning(f"处理多值字段失败: {data_key}/{xml_tag} - {e}")
            
    if 'releasedate' in data:
        data['release_date'] = data.pop('releasedate')
        
    return data

def extract_bangou_from_title(title_str):
    """从标题中提取番号和清理后的标题"""
    match = re.search(r'([A-Z]{2,5}-\d{2,5})', title_str.upper())
    if match:
        bangou = match.group(1)
        clean_title = title_str.replace(bangou, '').strip()
        return bangou, clean_title
    return "N/A", title_str

def save_nfo_file(nfo_path, data, mode='handmade'):
    """
    保存NFO文件，使用XML树重建方式
    mode: 'handmade' - 手作修正模式，只更新NFO文件
          'database' - 数据库清洗模式，同步更新NFO和数据库
    """
    try:
        if not data:
            return False, "没有提供要保存的数据"
        
        # 检查目标目录是否存在，不存在则创建
        target_dir = os.path.dirname(nfo_path)
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
                logger.info(f"已创建NFO文件目录: {target_dir}")
            except Exception as e:
                logger.error(f"创建目录失败: {target_dir} - {e}")
                return False, f"创建目录失败: {e}"
        
        # 处理字段可能为None或非字符串的情况
        for key in list(data.keys()):
            if data[key] is None:
                data[key] = ''
            elif not isinstance(data[key], (str, list)):
                data[key] = str(data[key])
        
        # 自动复制字段: 将title复制到sorttitle, plot复制到outline
        if 'title' in data:
            data['sorttitle'] = data['title']
            
        if 'plot' in data:
            data['outline'] = data['plot']
        
        # 直接复用字段数据: label→publisher, studio→maker, release_date→releasedate/premiered/release
        if 'label' in data and data.get('label'):
            data['publisher'] = data['label']
        
        if 'studio' in data and data.get('studio'):
            data['maker'] = data['studio']
            
        if 'release_date' in data and data.get('release_date'):
            data['releasedate'] = data['release_date']
            data['premiered'] = data['release_date']
            data['release'] = data['release_date']
        elif 'year' in data and data.get('year'):
            # 如果没有release_date但有year，则设置为YYYY-01-01格式
            year_value = f"{data['year']}-01-01"
            data['release_date'] = year_value
            data['releasedate'] = year_value
            data['premiered'] = year_value
            data['release'] = year_value
            
        # 如果有评分但没有评级，则将评分乘以10设置为评级
        if 'rating' in data and data.get('rating') and ('criticrating' not in data or not data.get('criticrating')):
            try:
                rating_value = float(data['rating'])
                data['criticrating'] = str(rating_value * 10)
            except (ValueError, TypeError):
                # 如果评分无法转换为浮点数，则直接复制
                data['criticrating'] = data['rating']
        
        # 拼接番号（仅适用于数据库清洗模式）
        if mode == 'database' and 'title' in data and 'num' in data:
            bangou = data.get('num', '')
            title = data.get('title', '')
            if bangou and not bangou in title:
                data['title'] = f"{bangou} {title}"
                # 同时更新sorttitle
                data['sorttitle'] = data['title']
            
            originaltitle = data.get('originaltitle', '')
            if bangou and not bangou in originaltitle and originaltitle:
                data['originaltitle'] = f"{bangou} {originaltitle}"
        
        # 需要保留的现有字段列表
        preserve_fields = ['countrycode', 'customrating', 'mpaa', 'cover', 'runtime', 'website']
        
        # 如果文件已存在，先读取保留字段
        if os.path.exists(nfo_path):
            try:
                tree = ET.parse(nfo_path)
                root = tree.getroot()
                
                # 保留特定字段的值
                for field in preserve_fields:
                    elem = root.find(field)
                    if elem is not None and elem.text and field not in data:
                        data[field] = elem.text.strip()
            except Exception as e:
                logger.warning(f"读取现有NFO文件失败，将创建新文件: {e}")
        
        # 创建新的XML树
        root = ET.Element('movie')
        
        # 需要CDATA包裹的字段
        cdata_fields = ['title', 'originaltitle', 'sorttitle', 'plot', 'originalplot', 'outline']
        
        # 优先添加一些关键字段，保持一定顺序
        order_fields = ['title', 'originaltitle', 'sorttitle', 'num', 'tagline', 'countrycode', 
                        'customrating', 'mpaa', 'studio', 'maker', 'publisher', 'label', 'plot', 
                        'originalplot', 'outline', 'runtime', 'premiered', 'releasedate', 'release', 
                        'year', 'rating', 'criticrating', 'cover', 'website']
        
        # 添加有序字段
        for field in order_fields:
            if field in data and data[field]:
                elem = ET.SubElement(root, field)
                elem.text = data[field]
        
        # 添加其他单值字段
        for field, value in data.items():
            # 跳过已添加的字段、内部字段和多值字段
            if field in order_fields or field.startswith('_') or isinstance(value, list):
                continue
                
            elem = ET.SubElement(root, field)
            elem.text = value
        
        # 添加多值字段
        multi_fields = {'sets': 'set', 'actors': 'actor', 'genres': 'genre', 'tags': 'tag'}
        # 按指定顺序添加多值字段
        for data_key, xml_tag in [('sets', 'set'), ('actors', 'actor'), ('genres', 'genre'), ('tags', 'tag')]:
            values = data.get(data_key)
            if not values:
                continue
                
            for item_value in values:
                item_elem = ET.SubElement(root, xml_tag)
                if xml_tag in ['actor', 'set']:
                    name_elem = ET.SubElement(item_elem, 'name')
                    name_elem.text = item_value
                else:
                    item_elem.text = item_value
        
        # 格式化XML
        ET.indent(tree=root, space="  ", level=0)
        
        # 转换为字符串
        xml_string = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')
        
        # 添加CDATA标记
        for field in cdata_fields:
            if field in data and data[field]:
                try:
                    pattern = f"<{field}>(.*?)</{field}>"
                    replacement = f"<{field}><![CDATA[\\1]]></{field}>"
                    xml_string = re.sub(pattern, replacement, xml_string, flags=re.DOTALL)
                except Exception as e:
                    logger.warning(f"添加CDATA标记失败: {field} - {e}")
        
        # 确保XML声明使用标准格式
        xml_string = xml_string.replace('<?xml version=\'1.0\' encoding=\'utf-8\'?>', 
                                      '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')
        
        # 写入文件
        try:
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml_string)
        except Exception as e:
            logger.error(f"写入NFO文件失败: {nfo_path} - {e}")
            return False, f"写入NFO文件失败: {e}"
            
        return True, "NFO文件保存成功"
    except Exception as e:
        logger.error(f"保存NFO文件失败: {nfo_path} - {e}")
        return False, f"保存NFO文件失败: {e}"