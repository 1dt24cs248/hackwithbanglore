const blockStart = (line) =>
  /^\s*(?:#{1,6}\s+|> ?|[-+*]\s+|\d+[.)]\s+|```|(?:---|\*\*\*|___)\s*$)/.test(line)

export function parseInlineMarkdown(source) {
  const tokens = []
  const pattern = /\\([\\`*_{}\[\]()#+.!|>~-])|(`+)(.*?)\2|(\*\*|__)(.+?)\4|(\*|_)(.+?)\6/g
  let lastIndex = 0
  let match

  while ((match = pattern.exec(source)) !== null) {
    if (match.index > lastIndex) tokens.push({ type: 'text', value: source.slice(lastIndex, match.index) })
    if (match[1] !== undefined) tokens.push({ type: 'text', value: match[1] })
    else if (match[2] !== undefined) tokens.push({ type: 'code', value: match[3] })
    else if (match[4] !== undefined) tokens.push({ type: 'strong', children: parseInlineMarkdown(match[5]) })
    else tokens.push({ type: 'emphasis', children: parseInlineMarkdown(match[7]) })
    lastIndex = pattern.lastIndex
  }

  if (lastIndex < source.length) tokens.push({ type: 'text', value: source.slice(lastIndex) })
  return tokens
}

export function parsePostmortemMarkdown(markdown) {
  const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n')
  const blocks = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    if (!line.trim()) { index += 1; continue }

    const fence = line.match(/^\s*```([^`]*)$/)
    if (fence) {
      const body = []
      index += 1
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) body.push(lines[index++])
      if (index < lines.length) index += 1
      blocks.push({ type: 'codeBlock', language: fence[1].trim(), value: body.join('\n') })
      continue
    }

    if (/^\s*(?:---|\*\*\*|___)\s*$/.test(line)) {
      blocks.push({ type: 'rule' })
      index += 1
      continue
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/)
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, children: parseInlineMarkdown(heading[2]) })
      index += 1
      continue
    }

    if (/^\s*>/.test(line)) {
      const quoteLines = []
      while (index < lines.length && /^\s*>/.test(lines[index])) {
        quoteLines.push(lines[index++].replace(/^\s*> ?/, ''))
      }
      blocks.push({ type: 'quote', children: quoteLines.map(parseInlineMarkdown) })
      continue
    }

    const listItem = line.match(/^\s*([-+*]|\d+[.)])\s+(.+)$/)
    if (listItem) {
      const ordered = /^\d/.test(listItem[1])
      const items = []
      while (index < lines.length) {
        const item = lines[index].match(/^\s*([-+*]|\d+[.)])\s+(.+)$/)
        if (!item || /^\d/.test(item[1]) !== ordered) break
        items.push(parseInlineMarkdown(item[2]))
        index += 1
      }
      blocks.push({ type: ordered ? 'orderedList' : 'unorderedList', items })
      continue
    }

    const paragraph = [line.trim()]
    index += 1
    while (index < lines.length && lines[index].trim() && !blockStart(lines[index])) {
      paragraph.push(lines[index].trim())
      index += 1
    }
    blocks.push({ type: 'paragraph', children: parseInlineMarkdown(paragraph.join(' ')) })
  }

  return blocks
}

export function createPostmortemMarkdownBlob(markdown) {
  return new Blob([typeof markdown === 'string' ? markdown : ''], { type: 'text/markdown;charset=utf-8' })
}
