"""
微信公众号文章预处理 + 批量抽取脚本

流程:
  1. 读取 newdata.json，筛选 108 篇事故详情
  2. 清洗微信噪声 → 纯文本
  3. 智能分段（3000字/段，段落边界）
  4. LLM 抽取（复用现有 Prompt Chain）
  5. Neo4j MERGE + SQLite INSERT 双写入
  6. 统计报告

用法: python scripts/process_wechat_data.py
"""
import os, sys, re, json, time, logging
from pathlib import Path
from datetime import datetime
from collections import Counter

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("wechat")

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

DATA_FILE = Path("../newdata.json")
OUTPUT_DIR = Path("data/raw/wechat_reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
#  阶段一: 预处理
# ═══════════════════════════════════════════════════════════════════
def load_and_filter():
    """加载数据，筛选事故详情类"""
    with open(DATA_FILE, encoding='utf-8') as f:
        data = json.load(f)

    accidents = []
    for a in data:
        t = a.get('title', '')
        c = str(a.get('content', ''))
        d = a.get('digest', '')
        if len(c) < 300:
            continue
        if not re.search(r'事故|爆炸|泄漏|中毒|火灾|伤亡|爆燃|闪爆', t):
            continue
        if not re.search(r'原因|分析|调查|经过|处置|施救|救援|教训|警示|防范|措施|整改|直接原因|间接原因', c):
            continue
        accidents.append(a)

    logger.info(f"筛选: {len(accidents)}/{len(data)} 篇事故详情")
    return accidents


def clean_wechat_text(text: str) -> str:
    """清洗微信文章噪声"""
    # 移除引导关注语
    text = re.sub(r'点击上方蓝字.*?关注.*?\n?', '', text)
    text = re.sub(r'点击.*?关注.*?公众号.*?\n?', '', text)
    text = re.sub(r'微信号[：:]\s*\S+\s*\n?', '', text)
    text = re.sub(r'长按.*?识别.*?关注.*?\n?', '', text)
    # 移除编辑/来源信息
    text = re.sub(r'编辑[：:].*?\n', '', text)
    text = re.sub(r'来源[：:].*?\n', '', text)
    text = re.sub(r'责编[：:].*?\n', '', text)
    text = re.sub(r'审核[：:].*?\n', '', text)
    # 移除图片占位和二维码
    text = re.sub(r'\[图片\]', '', text)
    text = re.sub(r'\(图片.*?\)', '', text)
    text = re.sub(r'二维码', '', text)
    text = re.sub(r'阅读\s*\d+', '', text)
    text = re.sub(r'点赞\s*\d+', '', text)
    # 移除HTML标签残留
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    # 规范化空白
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def split_into_chunks(text: str, max_chars: int = 2500, overlap: int = 200) -> list:
    """智能分段：按段落边界切分，保留重叠区以维持因果链完整"""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split('\n')
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if current_len + len(para) > max_chars and current:
            chunks.append('\n'.join(current))
            # 保留最后一段作为重叠
            overlap_text = current[-1] if current else ''
            current = [overlap_text] if overlap_text and len(overlap_text) < overlap else []
            current_len = len(overlap_text) if current else 0

        current.append(para)
        current_len += len(para)

    if current:
        chunks.append('\n'.join(current))

    return chunks


def preprocess(accidents):
    """预处理所有文章，保存清洗后的txt"""
    stats = {"total": len(accidents), "chunks": 0, "saved": 0}
    manifest = []

    for a in accidents:
        title = a.get('title', 'untitled')
        raw = str(a.get('content', ''))
        digest = a.get('digest', '')

        # 清洗
        cleaned = clean_wechat_text(raw)

        # 构建完整文本（标题+摘要+正文）
        full_text = f"标题: {title}\n"
        if digest and len(digest) > 10:
            full_text += f"摘要: {digest}\n"
        full_text += f"{'='*50}\n{cleaned}"

        # 分段
        chunks = split_into_chunks(full_text, max_chars=2500)
        stats["chunks"] += len(chunks)

        # 保存每段为独立文件
        safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:60]
        for i, chunk in enumerate(chunks):
            fname = f"{safe_title}_p{i}.txt" if len(chunks) > 1 else f"{safe_title}.txt"
            fpath = OUTPUT_DIR / fname
            fpath.write_text(chunk, encoding='utf-8')
            stats["saved"] += 1
            manifest.append({
                "file": str(fpath),
                "title": title,
                "chunk": i,
                "total_chunks": len(chunks),
                "chars": len(chunk),
            })

    # 保存清单
    with open(OUTPUT_DIR / "manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"预处理: {stats['total']}篇 → {stats['chunks']}段 → {stats['saved']}个txt")
    return stats, manifest


# ═══════════════════════════════════════════════════════════════════
#  阶段二: LLM 抽取
# ═══════════════════════════════════════════════════════════════════
def run_extraction(manifest):
    """对清洗后的文件运行 LLM 抽取"""
    from src.extraction.entity_extractor import EntityExtractor
    from src.extraction.result_validator import ResultValidator
    from src.storage.neo4j_client import Neo4jClient
    from src.storage.schema_manager import GraphSchema

    extractor = EntityExtractor()
    validator = ResultValidator()
    neo4j = Neo4jClient()
    neo4j.connect()

    if neo4j.graph is None:
        logger.error("Neo4j 未连接")
        return

    GraphSchema.create_index_constraints(neo4j.graph)

    before_nodes = neo4j.get_entity_count()
    before_rels = neo4j.get_relation_count()
    logger.info(f"入库前: {before_nodes} 节点, {before_rels} 关系")

    stats = {"total": 0, "success": 0, "failed": 0, "total_triples": 0}
    batch_triples = []
    batch_type_maps = []
    batch_size = 5

    # 按文章分组，同一篇文章的多个chunk连续处理
    files = sorted(Path(f).resolve() for f in [m["file"] for m in manifest])
    seen_titles = set()

    for i, fpath in enumerate(files):
        if not fpath.exists():
            continue

        raw = fpath.read_text(encoding='utf-8')
        title_match = re.search(r'标题:\s*(.+)', raw)
        title = title_match.group(1).strip() if title_match else fpath.stem

        # 去标题行的正文
        accident_text = re.sub(r'^标题:.*\n', '', raw)
        accident_text = re.sub(r'^摘要:.*\n', '', accident_text)
        accident_text = re.sub(r'^=+\n', '', accident_text)
        accident_text = accident_text.strip()

        if len(accident_text) < 50:
            continue

        stats["total"] += 1
        is_new_article = title not in seen_titles
        seen_titles.add(title)

        prefix = "★ " if is_new_article else "  "
        logger.info(f"{prefix}[{stats['total']}/{len(files)}] {title[:50]:50s} ({len(accident_text)}字)")

        # LLM 抽取
        try:
            result = extractor.extract_from_text(accident_text)
        except Exception as e:
            logger.warning(f"    LLM调用失败: {e}")
            stats["failed"] += 1
            continue

        if not result or not validator.validate_structure(result):
            logger.warning(f"    抽取结果无效")
            stats["failed"] += 1
            continue

        # 转三元组
        type_map = extract_entity_type_map(result)
        triples = extractor.convert_to_triples(result)

        if not triples:
            stats["failed"] += 1
            continue

        batch_triples.extend(triples)
        batch_type_maps.append(type_map)
        stats["success"] += 1
        stats["total_triples"] += len(triples)

        # 统计实体类型
        etypes = set(type_map.values())
        has_mitigation = "Mitigation" in etypes
        flag = " [含Mitigation!]" if has_mitigation else ""
        logger.info(f"    → {len(triples)}条三元组, 类型:{etypes}{flag}")

        # 批量写入
        if len(batch_triples) >= batch_size * 3:  # 大约15条三元组一批
            _flush(neo4j, batch_triples, batch_type_maps, fpath)
            # 同时写 SQLite
            _save_to_sqlite(fpath, raw, accident_text, result, type_map)
            batch_triples = []
            batch_type_maps = []

    # 尾批
    if batch_triples:
        _flush(neo4j, batch_triples, batch_type_maps, "final_batch")

    after_nodes = neo4j.get_entity_count()
    after_rels = neo4j.get_relation_count()

    logger.info(f"\n{'='*60}")
    logger.info(f"抽取完成: {stats['success']}成功/{stats['failed']}失败")
    logger.info(f"三元组: {stats['total_triples']}条")
    logger.info(f"Neo4j: {before_nodes}→{after_nodes}节点 (+{after_nodes-before_nodes})")
    logger.info(f"       {before_rels}→{after_rels}关系 (+{after_rels-before_rels})")

    # Mitigation 增长
    try:
        r = neo4j.graph.run("MATCH (n:Mitigation) RETURN count(n) as c").data()
        logger.info(f"Mitigation节点: {r[0]['c']}")
    except Exception:
        pass

    return stats


def extract_entity_type_map(result):
    """从LLM抽取结果提取实体类型映射"""
    type_map = {}
    for item in result.get("event_chain", []):
        if "entity" in item and "type" in item:
            type_map[item["entity"]] = item["type"]
        if "relation" in item and "target" in item:
            target = item["target"]
            if target not in type_map:
                type_map[target] = "Abnormal_Condition"
    return type_map


def _flush(neo4j, triples, type_maps, source):
    merged = {}
    for tm in type_maps:
        merged.update(tm)
    neo4j.batch_create_triples(triples, entity_type_map=merged, source_report=str(source))


def _save_to_sqlite(file_path, raw_text, accident_text, llm_result, type_map):
    """写入 SQLite（与现有 run_extraction_pipeline 逻辑一致）"""
    try:
        from config.database import SessionLocal
        from src.storage.relational_db import AccidentRecord

        title_match = re.search(r"标题:\s*(.+)", raw_text)
        title = title_match.group(1).strip() if title_match else Path(file_path).stem

        root_cause = llm_result.get("root_cause", "")
        consequence = llm_result.get("consequence", "")
        chemicals = ",".join([name for name, t in type_map.items() if t == "Material"])
        equipments = ",".join([name for name, t in type_map.items() if t == "Equipment"])

        session = SessionLocal()
        existing = session.query(AccidentRecord).filter_by(title=title).first()
        if not existing:
            session.add(AccidentRecord(
                title=title,
                summary=accident_text[:500],
                source_url="wechat:ciedu",
                root_cause=root_cause,
                consequence=consequence,
                related_chemicals=chemicals,
                related_equipment=equipments,
            ))
            session.commit()
        session.close()
    except Exception as e:
        logger.debug(f"SQLite写入跳过: {e}")


# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  微信公众号数据 → ChemSafe-KG 知识图谱")
    logger.info("=" * 60)

    # 阶段一
    accidents = load_and_filter()
    stats, manifest = preprocess(accidents)

    # 阶段二
    logger.info(f"\n开始 LLM 抽取 ({len(manifest)} 个文件)...")
    run_extraction(manifest)

    logger.info("\n全部完成")
