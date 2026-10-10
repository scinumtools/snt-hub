local version_file = assert(io.open("VERSION", "r"), "Run Pandoc from the SNT Hub repository root: VERSION was not found")
local version = version_file:read("*l") or ""
version_file:close()

assert(version:match("^%d+%.%d+%.%d+[%w%.%-]*$"), "Invalid SNT Hub VERSION: " .. version)

function Meta(meta)
  local subtitle = pandoc.utils.stringify(meta.subtitle or "")
  local rendered = pandoc.read(subtitle .. " | SNT Hub v" .. version, "markdown")
  meta.subtitle = pandoc.MetaInlines(rendered.blocks[1].content)
  return meta
end
