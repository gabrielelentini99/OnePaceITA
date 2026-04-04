param([string]$ep)
Set-Location "C:\Users\gabri\OneDrive\Desktop\One Pace"
$file = "sources\32 Wano\$ep\wano $ep en.ass"
$content = Get-Content $file -Encoding UTF8
$output = @()
foreach ($line in $content) {
    if ($line -notmatch '^Dialogue:') { continue }
    $p = $line -split ',', 10
    if ($p.Count -lt 10) { continue }
    $style = $p[3].Trim()
    if ($style -notmatch 'Main-207\+|Secondary-207\+|Flashbacks-207\+|Thoughts-207\+|Narrator-207\+') { continue }
    $start = $p[1].Trim()
    $end = $p[2].Trim()
    $text = $p[9]
    $text = [regex]::Replace($text, '\{[^}]*\}', '')
    $text = $text -replace '\\N', "`n"
    $text = $text.Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { continue }
    # Convert ASS time to SRT time: 0:01:42.91 -> 00:01:42,910
    function ToSRT($t) {
        if ($t -match '^(\d):(\d{2}):(\d{2})\.(\d{2,3})$') {
            $h = "0" + $matches[1]; $m = $matches[2]; $s = $matches[3]
            $ms = $matches[4].PadRight(3, '0')
            return "${h}:${m}:${s},${ms}"
        }
        return $t
    }
    $output += [PSCustomObject]@{
        Start = ToSRT $start
        End   = ToSRT $end
        Text  = $text
    }
}
Write-Host "Lines: $($output.Count)"
# Output as numbered SRT-like for review
$i = 1
foreach ($item in $output) {
    Write-Output "==$i=="
    Write-Output "$($item.Start) --> $($item.End)"
    Write-Output $item.Text
    $i++
}
