"""
事故报告爬虫模块

负责从多个公开数据源爬取/下载化工安全事故调查报告。
支持 PDF 和 HTML 两种格式的事故报告获取。

已实现解析逻辑的数据源:
  - mem.gov.cn (P1): "历史上的危化品事故"栏目 ✅
  - CSB (P2): 调查报告列表 ✅ (浏览器渲染页面，requests 降级可用)
  - ciedu.com.cn (P0): ❌ 网站 502 不可达

数据源信息（来自材料.md）:
  - 化工安全教育公共服务平台: https://ciedu.com.cn (推荐 P0) *当前不可达*
  - 应急管理部官网警示信息: https://www.mem.gov.cn (P1)
  - CSB (美国化学品安全委员会): https://www.csb.gov (P2)
  - ChemSafe 化工安全事故案例库: https://www.ichemsafe.com (P2)
  - NTSB: https://www.ntsb.gov (P2)
  - eMARS: https://emars.jrc.ec.europa.eu (P2)
"""
import re
import time
import logging
from pathlib import Path
from typing import Optional, List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, Tag
from config.settings import crawler as crawler_config, paths

logger = logging.getLogger(__name__)


class ReportCrawler:
    """化工事故报告爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": crawler_config.USER_AGENT,
            "Accept": "text/html,application/pdf,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.output_dir = paths.REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─── 数据源定义 ─────────────────────────────────────────────────────────
    CRAWL_SOURCES = {
        # P0
        "ciedu_cases": {
            "url": "https://ciedu.com.cn",
            "type": "html",
            "channel": "应急管理、安全生产事故案例",
            "description": "化工安全教育公共服务平台 - 事故案例频道（当前502不可达）",
            "priority": "P0",
        },
        # P1
        "chem_safety_org": {
            "url": "https://www.chemicalsafety.org.cn/shiguxinxi/shiguanli",
            "type": "html",
            "description": "中国化学品安全协会 - 事故信息/事故案例管理",
            "priority": "P1",
        },
        "mem_warning": {
            "url": "https://www.mem.gov.cn/fw/jsxx/lssdwhpsg/",
            "type": "html",
            "channel": "警示信息 > 历史上的危化品事故",
            "description": "应急管理部官网 - 按月发布的典型危化品事故案例（含国内外化工事故及根因分析）",
            "priority": "P1",
        },
        "mem_public_info": {
            "url": "http://www.mem.gov.cn",
            "type": "html",
            "channel": "政府信息公开 > 安全生产事故通报",
            "description": "应急管理部 - 公开的安全生产事故通报、调查报告",
            "priority": "P1",
        },
        # P2
        "csb_reports": {
            "url": "https://www.csb.gov/investigations/completed-investigations/",
            "type": "html",
            "description": "美国化学品安全委员会 (CSB) 已完成调查的化工安全事故报告",
            "priority": "P2",
        },
        "csb_incident_reports": {
            "url": "https://www.csb.gov/incident-reports/",
            "type": "html",
            "description": "CSB 2025年事故简报系列（当前404不可达）",
            "priority": "P2",
        },
        "ichemsafe": {
            "url": "https://www.ichemsafe.com",
            "type": "html",
            "description": "ChemSafe 化工安全事故案例库",
            "priority": "P2",
        },
        "ntsb": {
            "url": "https://www.ntsb.gov",
            "type": "html",
            "description": "美国国家运输安全委员会 - 化工运输事故调查",
            "priority": "P2",
        },
        "emars": {
            "url": "https://emars.jrc.ec.europa.eu",
            "type": "html",
            "description": "欧盟/经合组织化学品事故报告系统 (eMARS)",
            "priority": "P2",
        },
    }

    # 固定分类标题（短文本，非事故）
    _CATEGORY_HEADERS = frozenset({
        "石油化工", "煤化工", "精细化工", "有机化工", "无机化工",
        "化肥", "农药", "医药", "其他",
    })

    # =====================================================================
    #  fetch_report_list — 数据源分派
    # =====================================================================
    def fetch_report_list(self, source_key: str, max_reports: int = 0) -> list[dict]:
        """
        爬取事故报告列表页，返回报告元信息列表。

        Args:
            source_key: 数据源键名
            max_reports: 最多返回多少条 (0 = 不限)

        返回:
            [{"title", "url", "date", "source", "text"}, ...]
            对 mem.gov.cn 数据源, text 字段已内嵌事故描述文本。
        """
        source = self.CRAWL_SOURCES.get(source_key)
        if not source:
            logger.warning(f"未知数据源: {source_key}")
            return []

        logger.info(f"从 {source_key} ({source['url']}) 获取报告列表...")

        if source_key == "mem_warning":
            return self._parse_mem_accidents(source["url"], max_accidents=max_reports)
        elif source_key == "csb_reports":
            return self._parse_csb_list(source["url"])
        else:
            logger.warning(f"数据源 '{source_key}' 的解析器尚未实现")
            return []

    # =====================================================================
    #  mem.gov.cn — "历史上的危化品事故"
    # =====================================================================
    # 页面结构实测 (2026-05):
    #   列表页: /fw/jsxx/lssdwhpsg/ (5 页, index_1..4.shtml 为 2-5 页)
    #   月度详情页:
    #     <div class="cont">
    #       <p><strong>一、2026年4月发生的典型事故</strong></p>  ← 章节(strong)
    #       <p>甘肃酒泉金特化学公司"4·6"较大闪爆事故</p>         ← 事故标题(纯<p>!)
    #       <p>2026年4月6日...事故直接原因是...</p>               ← 描述
    #       <p>石油化工</p>                                       ← 分类(短文本)
    #       <p>中石化上海赛科..."5·12"较大闪爆事故</p>           ← 事故标题
    #       ...

    MEM_LIST_BASE = "https://www.mem.gov.cn/fw/jsxx/lssdwhpsg"

    def _parse_mem_list_pages(self) -> list[dict]:
        """爬取 mem.gov.cn 月度汇编列表页（共 5 页），返回所有月度条目元信息。"""
        page_urls = [self.MEM_LIST_BASE + "/"] + [
            f"{self.MEM_LIST_BASE}/index_{i}.shtml" for i in range(1, 5)
        ]
        monthly_entries = []

        for url in page_urls:
            try:
                resp = self.session.get(url, timeout=crawler_config.TIMEOUT)
                resp.raise_for_status()
                resp.encoding = "utf-8"
            except requests.RequestException as e:
                logger.warning(f"列表页请求失败 [{url}]: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # 列表中的链接: 如 /fw/jsxx/202604/t20260430_602285.shtml
            for a_tag in soup.find_all("a", href=re.compile(r"t\d+_\d+\.shtml")):
                text = a_tag.get_text(strip=True)
                if "危险化学品事故" not in text:
                    continue

                href = a_tag.get("href", "")
                # 使用 urljoin 正确解析相对路径 (如 ../202604/t20260430_602285.shtml)
                full_url = urljoin(url, href)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)

                monthly_entries.append({
                    "title": text.strip(),
                    "url": full_url,
                    "date": date_match.group(1) if date_match else "",
                    "source": "mem.gov.cn",
                })

            time.sleep(crawler_config.DELAY)

        logger.info(f"mem.gov.cn 列表页: {len(monthly_entries)} 条月度汇编")
        return monthly_entries

    def _parse_mem_accidents(self, list_url: str, max_accidents: int = 0) -> list[dict]:
        """
        爬取月度汇编页并提取独立事故，返回扁平化事故列表。

        Args:
            list_url: 列表页 URL
            max_accidents: 最多提取多少起事故 (0 = 不限)
        """
        monthly_entries = self._parse_mem_list_pages()
        if not monthly_entries:
            return []

        all_accidents = []
        for i, entry in enumerate(monthly_entries):
            logger.info(f"  月度 [{i+1}/{len(monthly_entries)}]: {entry['title'][:32]}...")

            try:
                resp = self.session.get(entry["url"], timeout=crawler_config.TIMEOUT)
                resp.raise_for_status()
                resp.encoding = "utf-8"
            except requests.RequestException as e:
                logger.warning(f"  请求失败: {e}")
                continue

            accidents = self._extract_accidents_from_page(
                html_text=resp.text,
                month_label=entry["title"],
                source_url=entry["url"],
            )
            all_accidents.extend(accidents)
            logger.info(f"    → {len(accidents)} 起事故 (累计 {len(all_accidents)})")

            # 如果已达到目标数量, 提前停止
            if max_accidents > 0 and len(all_accidents) >= max_accidents:
                all_accidents = all_accidents[:max_accidents]
                logger.info(f"  已达到目标 {max_accidents} 起, 提前停止")
                break

            time.sleep(crawler_config.DELAY)

        logger.info(f"mem.gov.cn 共提取 {len(all_accidents)} 起事故")
        return all_accidents

    def _extract_accidents_from_page(
        self, html_text: str, month_label: str, source_url: str,
    ) -> list[dict]:
        """
        从一篇月度汇编 HTML 中提取每起独立事故。

        算法: 逐段扫描 <div class="cont"> 中的 <p>,
        用简单特征区分章节标题 / 分类标题 / 事故标题 / 描述文本。
        """
        soup = BeautifulSoup(html_text, "lxml")
        content_div = (
            soup.find("div", class_="cont")
            or soup.find("div", class_=re.compile(r"con_main|article|content", re.I))
            or soup.find("div", id=re.compile(r"content|article|UCAP-CONTENT", re.I))
            or soup.find("body")
        )
        paragraphs = content_div.find_all("p", recursive=True) if isinstance(content_div, Tag) else []

        accidents = []
        current_title: Optional[str] = None
        current_paras: list[str] = []

        def flush():
            nonlocal current_title, current_paras
            if current_title and current_paras:
                text = "\n".join(current_paras).strip()
                # 优先从事故描述中提取具体日期, 其次从月标签中提取
                date_str = ""
                date_from_text = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
                if date_from_text:
                    date_str = f"{date_from_text.group(1)}-{date_from_text.group(2).zfill(2)}-{date_from_text.group(3).zfill(2)}"
                else:
                    m = re.search(r"(\d{4})年(\d+)月", month_label or "")
                    if m:
                        date_str = f"{m.group(1)}-{m.group(2).zfill(2)}"
                accidents.append({
                    "title": current_title,
                    "text": text,
                    "url": source_url,
                    "date": date_str,
                    "source": "mem.gov.cn",
                    "monthly": month_label,
                })
            current_title = None
            current_paras = []

        for para in paragraphs:
            raw = para.get_text(strip=True)
            if not raw:
                continue

            # (1) 章节标题: <strong> 内是 "一、..." "2026年..." 等
            strong = para.find(["strong", "b"])
            if strong:
                st = strong.get_text(strip=True)
                if re.match(r'^[\d一二三四五六七八九十]+[、.．]', st) or \
                   re.match(r'^（[一二三四五六七八九十]+）', st) or \
                   re.match(r'\d{4}年\d{1,2}月', st):
                    flush()
                    continue

            # (2) 分类标题
            if raw in self._CATEGORY_HEADERS or raw in ("（一）国内事故", "（二）国外事故"):
                flush()
                continue

            # (3) 事故标题: 13~45 字符, 含事故/爆炸等关键词
            if self._is_accident_title(raw):
                flush()
                current_title = raw
                current_paras = []
                continue

            # (4) 描述
            if current_title:
                current_paras.append(raw)

        flush()
        return accidents

    def _is_accident_title(self, text: str) -> bool:
        """判断是否为事故标题。"""
        length = len(text)
        if length < 13 or length > 45:
            return False
        if not re.search(r'事故|爆炸|泄漏|火灾|中毒|爆燃|闪爆|窒息|灼伤|伤亡|燃烧', text):
            return False
        # 排除 "2026年4月发生的典型事故" 这种行
        if re.match(r'\d{4}年\d{1,2}月', text):
            return False
        return True

    # =====================================================================
    #  CSB — 调查报告列表解析
    # =====================================================================
    # CSB 页面 JS 动态渲染, requests 只能获取卡片 HTML 中嵌入的数据。
    # 完整采集请使用 browser tool。

    CSB_BASE = "https://www.csb.gov"

    def _parse_csb_list(self, list_url: str) -> list[dict]:
        """从 CSB 已完成调查页面提取调查条目。"""
        try:
            resp = self.session.get(list_url, timeout=crawler_config.TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
        except requests.RequestException as e:
            logger.warning(f"CSB 请求失败 [{list_url}]: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        reports = []

        # 尝试多种选择器匹配调查卡片
        cards = soup.select(
            ".investigation-card, .completed-item, "
            "[class*='investigation'], [class*='completed'], "
            ".views-row, .node--type-investigation"
        )
        if not cards:
            # 也尝试从列表项提取
            cards = soup.find_all("li", class_=re.compile(r"investigation|completed", re.I))

        for card in cards:
            title_el = card.select_one("h2 a, h3 a, a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            full_url = href if href.startswith("http") else self.CSB_BASE + href

            # 提取日期和描述
            date_text = ""
            desc_text = ""
            for span in card.find_all(["span", "p", "div"]):
                st = span.get_text(strip=True)
                dm = re.search(r"(\d{2}/\d{2}/\d{4})", st)
                if dm and not date_text:
                    date_text = dm.group(1)
                if len(st) > 60 and not desc_text:
                    desc_text = st

            reports.append({
                "title": title,
                "url": full_url,
                "date": date_text,
                "text": desc_text,
                "source": "csb.gov",
            })

        if reports:
            logger.info(f"CSB: {len(reports)} 条调查 (requests)")
        else:
            logger.warning(
                "CSB 页面 JS 渲染，requests 无法获取完整列表。"
                "请用 browser tool 手动采集。"
            )
        return reports

    # =====================================================================
    #  download_report — 下载/保存报告
    # =====================================================================
    def download_report(self, report_url: str, save_name: Optional[str] = None) -> Optional[Path]:
        """
        下载单份事故报告，保存为 .txt（HTML）或 .pdf。

        对于 mem.gov.cn: fetch_report_list() 已内嵌 text, 此方法主要供其他数据源使用。
        """
        if not save_name:
            path_part = report_url.rstrip("/").split("/")[-1].replace(".shtml", "")
            save_name = f"report_{path_part}_{int(time.time())}.txt"

        save_path = self.output_dir / save_name

        try:
            resp = self.session.get(report_url, timeout=crawler_config.TIMEOUT, stream=True)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")

            if "pdf" in content_type:
                save_path = save_path.with_suffix(".pdf")
                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                body = soup.find("body")
                raw_text = body.get_text(separator="\n", strip=True) if body else resp.text
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(raw_text)

            logger.info(f"下载成功: {save_path} ({save_path.stat().st_size / 1024:.1f} KB)")
            return save_path

        except requests.RequestException as e:
            logger.error(f"下载失败 [{report_url}]: {e}")
            return None

    # =====================================================================
    #  run — 完整爬取流程
    # =====================================================================
    def run(self, max_reports: int = 150, sources: Optional[list[str]] = None):
        """
        运行完整爬取流程。

        流程:
          1) 依次爬取各数据源的报告列表
          2) 将每条事故的文本保存到 data/raw/accident_reports/ 下
          3) 受 max_reports 限制

        Args:
            max_reports: 目标采集报告数量
            sources: 数据源列表 (默认: ["mem_warning"])
        """
        if sources is None:
            sources = ["mem_warning"]

        logger.info(f"开始爬取事故报告，目标数量: {max_reports}, 数据源: {sources}")

        all_reports = []
        for source_key in sources:
            reports = self.fetch_report_list(source_key, max_reports=max_reports)
            all_reports.extend(reports)
            logger.info(f"  {source_key}: {len(reports)} 条报告")

        if not all_reports:
            logger.warning("所有数据源均未返回报告")
            return

        count = 0
        for report in all_reports:
            if count >= max_reports:
                break

            if report.get("text"):
                # 已有内嵌文本 → 直接保存为 .txt
                title_slug = re.sub(r'[\\/:*?"<>|]', '', report["title"])[:60]
                save_path = self.output_dir / f"{title_slug}.txt"
                save_path.parent.mkdir(parents=True, exist_ok=True)

                header = (
                    f"标题: {report['title']}\n"
                    f"来源: {report['source']}\n"
                    f"日期: {report['date']}\n"
                    f"月度汇编: {report.get('monthly', '')}\n"
                    f"{'=' * 60}\n"
                )
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(header + report["text"])

                logger.info(f"保存: {save_path.name} ({len(report['text'])} 字符)")
                count += 1
            else:
                # 无内嵌文本 → 下载
                result = self.download_report(report["url"])
                if result:
                    count += 1

            if count % 20 == 0:
                logger.info(f"  进度: {count}/{min(max_reports, len(all_reports))}")

        logger.info(f"爬取完成，共 {count} 份事故报告 (目标 {max_reports})")
