# Clean HTML for Chrome Extension
param(
    [string]$InputFile = "out/index.html",
    [string]$OutputFile = "extension/index.html"
)

# Read the HTML file
$html = Get-Content $InputFile -Raw

# Remove all script tags and their content
$html = $html -replace '<script[^>]*>.*?</script>', '' -replace '<script[^>]*/>',''

# Remove all script-related attributes and tags
$html = $html -replace '\s*async=""', ''
$html = $html -replace '\s*defer=""', ''
$html = $html -replace '\s*noModule=""', ''
$html = $html -replace '\s*id="_R_"', ''

# Remove preload links for scripts
$html = $html -replace '<link[^>]*rel="preload"[^>]*as="script"[^>]*/?>', ''

# Remove hidden divs and React hydration markers
$html = $html -replace '<div hidden="">.*?</div>', ''
$html = $html -replace '<!--\$-->|<!--/\$-->', ''

# Clean up extra whitespace
$html = $html -replace '\s+', ' '
$html = $html -replace '>\s+<', '><'

# Write the cleaned HTML
$html | Set-Content $OutputFile -NoNewline

Write-Host "Cleaned HTML written to $OutputFile"