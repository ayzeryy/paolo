"""Dependency-free structural/link checks. Run from the repository root.

This is a strict HTMLParser-based project check, not a full HTML conformance validator.
Optional: --base-url http://127.0.0.1:8765/ checks HTTP delivery of local files.
"""
from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import urlopen
import re

ROOT = Path(__file__).resolve().parents[1]
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
PAGES = ['naturae.html', 'marca.html', 'producto.html', 'impacto.html', 'contacto.html']


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path, self.stack, self.nodes, self.ids = path, [], [], set()
        self.doctype = False

    def handle_decl(self, decl):
        self.doctype = decl.lower() == 'doctype html'

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs))
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'{self.path}: duplicate ID'
            self.ids.add(attrs['id'])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f'{self.path}: mismatched </{tag}> {self.stack}'
        self.stack.pop()


def check(base_url=None):
    documents = {}
    for path in [ROOT / 'index.html', *sorted((ROOT / 'paolo').glob('*.html'))]:
        text = path.read_text(encoding='utf-8')
        doc = Document(path.relative_to(ROOT))
        doc.feed(text)
        assert doc.doctype and not doc.stack, f'{path}: incomplete document'
        assert sum(tag == 'main' for tag, _ in doc.nodes) == 1
        assert sum(tag == 'h1' for tag, _ in doc.nodes) == 1
        assert any(t == 'html' and a.get('lang') == 'es' for t, a in doc.nodes)
        assert any(t == 'meta' and a.get('charset', '').lower() == 'utf-8' for t, a in doc.nodes)
        assert any(t == 'meta' and a.get('name') == 'viewport' for t, a in doc.nodes)
        documents[path.resolve()] = doc

    titles, descriptions, assets = set(), set(), set()
    for path, doc in documents.items():
        for tag, attrs in doc.nodes:
            assert not any(k.startswith('on') for k in attrs), f'{path}: inline handler'
            if attrs.get('target') == '_blank':
                assert {'noopener', 'noreferrer'} <= set(attrs.get('rel', '').split())
            if tag == 'img':
                assert 'alt' in attrs and int(attrs['width']) > 0 and int(attrs['height']) > 0
            if tag == 'script':
                assert 'defer' in attrs and attrs.get('src') == 'assets/js/main.js'
            refs = [attrs[k] for k in ('href', 'src', 'poster') if k in attrs]
            refs += [candidate.strip().split()[0] for candidate in attrs.get('srcset', '').split(',') if candidate.strip()]
            if attrs.get('property') == 'og:image':
                refs.append(attrs['content'])
            if attrs.get('http-equiv') == 'refresh':
                refs.append(attrs['content'].split('url=')[1])
            for ref in refs:
                assert not ref.startswith('/'), f'{path}: root-relative URL {ref}'
                url = urlsplit(ref)
                if url.scheme:
                    assert url.scheme in ('https', 'mailto', 'tel'), f'{path}: bad protocol {ref}'
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                assert target.is_relative_to(ROOT) and target.is_file(), f'{path}: missing {ref}'
                if url.fragment and target in documents:
                    assert url.fragment in documents[target].ids, f'{path}: missing fragment {ref}'
                assets.add(target)

        if path.name in PAGES:
            text = path.read_text(encoding='utf-8')
            title = re.search(r'<title>(.*?)</title>', text).group(1)
            desc = next(a['content'] for t, a in doc.nodes if t == 'meta' and a.get('name') == 'description')
            assert title not in titles and desc not in descriptions
            titles.add(title)
            descriptions.add(desc)
            active = [a['href'] for t, a in doc.nodes if t == 'a' and a.get('aria-current') == 'page']
            assert active == [path.name], f'{path}: incorrect active navigation'
            assert all(f'href="{name}"' in text for name in PAGES)
            assert 'assets/css/styles.css' in text and '<style>' not in text

    for file in (ROOT / 'paolo' / 'assets').rglob('*'):
        if file.is_file() and file.suffix in ('.jpg', '.webp', '.png', '.mp4'):
            assert file.resolve() in assets, f'Orphaned media: {file}'
    contact = (ROOT / 'paolo/contacto.html').read_text(encoding='utf-8')
    assert 'href="mailto:natunaturaee@gmail.com"' in contact
    assert 'href="tel:+50242251494"' in contact
    video = next(a for t, a in documents[(ROOT / 'paolo/naturae.html').resolve()].nodes if t == 'video')
    assert {'controls', 'muted', 'loop', 'playsinline', 'data-autoplay'} <= video.keys()
    assert 'autoplay' not in video and video['preload'] == 'metadata'
    if base_url:
        for path in sorted(assets | set(documents)):
            url = base_url.rstrip('/') + '/' + path.relative_to(ROOT).as_posix()
            with urlopen(url, timeout=15) as response:
                assert response.status == 200, url
    print(f'PASS: {len(documents)} HTML documents, 5 unique page titles/descriptions, '
          f'{len(assets)} local reference targets; markup, metadata, links, media, navigation'
          + (' and HTTP delivery.' if base_url else '.'))


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    check(parser.parse_args().base_url)
