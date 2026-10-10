local version_file = assert(io.open("VERSION", "r"), "Run Pandoc from the SNT Hub repository root: VERSION was not found")
local version = version_file:read("*l") or ""
version_file:close()

assert(version:match("^%d+%.%d+%.%d+[%w%.%-]*$"), "Invalid SNT Hub VERSION: " .. version)

function Meta(meta)
  local subtitle = pandoc.utils.stringify(meta.subtitle or "")
  local rendered = pandoc.read(subtitle .. " | SNT Hub v" .. version, "markdown")
  meta.subtitle = pandoc.MetaInlines(rendered.blocks[1].content)

  local orcid = pandoc.utils.stringify(meta.orcid or "")
  assert(orcid:match("^%d%d%d%d%-%d%d%d%d%-%d%d%d%d%-%d%d%d[%dX]$"), "Invalid ORCID in specification metadata")
  local author = pandoc.utils.stringify(meta.author or "")
  meta.author = pandoc.MetaInlines({
    pandoc.Str(author),
    pandoc.Space(),
    pandoc.RawInline("latex", "\\href{https://orcid.org/" .. orcid .. "}{\\raisebox{-0.2ex}{\\includegraphics[height=1em]{docs/orcid-id.png}}}"),
  })
  return meta
end
