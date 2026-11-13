# ============================================================================
# shopping-api interface acceptance script (backend self-test, repeatable)
# Usage (from the shopping-api directory):
#   powershell -ExecutionPolicy Bypass -File .\verify-api.ps1
# Prerequisite: MySQL running, shopping_analytics loaded, 8080 owned by this jar
# The script creates and then deletes its own test rows, so data returns to
# baseline (sessions 12205 / rules 5) after a successful run.
# NOTE: ASCII-only on purpose - parses identically under Windows PowerShell 5.1
#       and PowerShell 7 regardless of console code page.
# ============================================================================
$ErrorActionPreference = 'Continue'
$B = 'http://localhost:8080'
$script:fail = 0

function Check-Get {
    param([string]$Path, [string]$Expect = '')
    try {
        $r = Invoke-RestMethod "$B$Path" -TimeoutSec 20
        $s = ($r.data | ConvertTo-Json -Depth 6 -Compress)
        $len = if ($null -eq $s) { 0 } else { $s.Length }
        $ok = ($r.code -eq 200) -and ($len -gt 2)
        if ($Expect -ne '' -and $r.data -is [array] -and $r.data.Count -ne [int]$Expect) { $ok = $false }
        if (-not $ok) { $script:fail++ }
        $extra = if ($Expect -ne '') { " items=$($r.data.Count)/$Expect" } else { '' }
        Write-Host ("{0} {1,-52} code={2} len={3}{4}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $Path, $r.code, $len, $extra)
        return $r
    }
    catch {
        $script:fail++
        Write-Host "FAIL $Path -> $($_.Exception.Message)"
        return $null
    }
}

Write-Host ""
Write-Host "===== 1. common endpoints =====" -ForegroundColor Cyan
Check-Get '/api/common/health' | Out-Null
Check-Get '/api/common/dict/month' 12 | Out-Null
Check-Get '/api/common/dict/visitor-type' | Out-Null

Write-Host ""
Write-Host "===== 2. member-one endpoints =====" -ForegroundColor Cyan
Check-Get '/api/m1/overview' | Out-Null
Check-Get '/api/m1/monthly-trend' 12 | Out-Null
Check-Get '/api/m1/visitor-type' | Out-Null
Check-Get '/api/m1/traffic-source' 10 | Out-Null
Check-Get '/api/m1/page-depth' 5 | Out-Null
Check-Get '/api/m1/bounce-exit' 10 | Out-Null
Check-Get '/api/m1/region' | Out-Null
Check-Get '/api/m1/weekend' 2 | Out-Null
Check-Get '/api/m1/session/page?pageNum=1&pageSize=5' | Out-Null
Check-Get '/api/m1/session/1' | Out-Null

Write-Host ""
Write-Host "===== 3. member-two endpoints =====" -ForegroundColor Cyan
Check-Get '/api/m2/pagevalues' 6 | Out-Null
Check-Get '/api/m2/model/metrics' 2 | Out-Null
Check-Get '/api/m2/model/confusion' | Out-Null
Check-Get '/api/m2/model/confusion?model=LogisticRegression' | Out-Null
Check-Get '/api/m2/feature-importance' 12 | Out-Null
Check-Get '/api/m2/special-day' 6 | Out-Null
Check-Get '/api/m2/os' 8 | Out-Null
Check-Get '/api/m2/browser' | Out-Null
Check-Get '/api/m2/device' | Out-Null
Check-Get '/api/m2/visitor-purchase' | Out-Null
Check-Get '/api/m2/rule/list' | Out-Null
Check-Get '/api/m2/rule/page?pageNum=1&pageSize=10' | Out-Null

Write-Host ""
Write-Host "===== 4. rate unit convention (all rates must be 0..1) =====" -ForegroundColor Cyan
$ov = (Invoke-RestMethod "$B/api/m1/overview").data
$rateNames = @('conversionRate', 'bounceRate', 'exitRate', 'newVisitorRate', 'returningRate')
$bad = @()
foreach ($n in $rateNames) {
    $v = $ov.$n
    if (-not ($v -ge 0 -and $v -le 1)) { $bad += "$n=$v" }
}
if ($bad.Count -eq 0) {
    Write-Host ("PASS overview rates all within 0..1 -> cr={0} bounce={1} exit={2} new={3} ret={4}" -f $ov.conversionRate, $ov.bounceRate, $ov.exitRate, $ov.newVisitorRate, $ov.returningRate)
}
else {
    $script:fail++
    Write-Host "FAIL overview rate out of range: $($bad -join ', ')"
}
$vt = (Invoke-RestMethod "$B/api/m1/visitor-type").data
$vtBad = @($vt | Where-Object { $_.pct -gt 1 -or $_.pct -lt 0 })
if ($vtBad.Count -eq 0) { Write-Host "PASS visitor-type pct all within 0..1" } else { $script:fail++; Write-Host "FAIL visitor-type pct out of range" }

Write-Host ""
Write-Host "===== 5. session CRUD regression =====" -ForegroundColor Cyan
$newSession = @{
    administrative = 3; administrativeDuration = 120.5
    informational = 1; informationalDuration = 30.0
    productRelated = 25; productRelatedDuration = 1450.75
    bounceRates = 0.015; exitRates = 0.032; pageValues = 12.5; specialDay = 0.0
    month = 'Nov'; operatingSystems = 2; browser = 2; region = 1; trafficType = 2
    visitorType = 'Returning_Visitor'; weekend = 0; revenue = 1
} | ConvertTo-Json
$c = Invoke-RestMethod "$B/api/m1/session" -Method Post -Body $newSession -ContentType 'application/json; charset=utf-8'
$sid = $c.data.sessionId
if ($c.code -eq 200 -and $sid -gt 0 -and $c.data.pageDepth -eq 29) {
    Write-Host "PASS create session id=$sid (derived pageDepth=29 totalDuration=$($c.data.totalDuration) monthNum=$($c.data.monthNum))"
} else { $script:fail++; Write-Host "FAIL create session" }

$g = Invoke-RestMethod "$B/api/m1/session/$sid"
if ($g.code -eq 200 -and $g.data.pageValues -eq 12.5) { Write-Host "PASS read back single row pageValues=$($g.data.pageValues)" } else { $script:fail++; Write-Host "FAIL read back" }

$updSession = @{
    administrative = 9; administrativeDuration = 999.9
    informational = 2; informationalDuration = 60.0
    productRelated = 50; productRelatedDuration = 3000.5
    bounceRates = 0.2; exitRates = 0.15; pageValues = 88.88; specialDay = 0.6
    month = 'Dec'; operatingSystems = 3; browser = 5; region = 4; trafficType = 7
    visitorType = 'New_Visitor'; weekend = 1; revenue = 0
} | ConvertTo-Json
$u = Invoke-RestMethod "$B/api/m1/session/$sid" -Method Put -Body $updSession -ContentType 'application/json; charset=utf-8'
if ($u.code -eq 200 -and $u.data.monthNum -eq 12 -and $u.data.isBounce -eq 1) {
    Write-Host "PASS update session (monthNum resolved=12, isBounce recomputed=1)"
} else { $script:fail++; Write-Host "FAIL update session" }

$p = Invoke-RestMethod "$B/api/m1/session/page?pageNum=1&pageSize=5&month=Dec&visitorType=New_Visitor"
if ($p.code -eq 200 -and $p.data.total -ge 1) { Write-Host "PASS paged filter total=$($p.data.total)" } else { $script:fail++; Write-Host "FAIL paged filter" }

$d = Invoke-RestMethod "$B/api/m1/session/$sid" -Method Delete
if ($d.code -eq 200 -and $d.data -eq $true) { Write-Host "PASS delete session" } else { $script:fail++; Write-Host "FAIL delete session" }
$after = Invoke-RestMethod "$B/api/m1/session/$sid"
if ($after.code -eq 500) { Write-Host "PASS query-after-delete returns code=500 (row gone)" } else { $script:fail++; Write-Host "FAIL row still present after delete" }

Write-Host ""
Write-Host "===== 6. alert rule CRUD regression =====" -ForegroundColor Cyan
$ruleBody = @{ ruleName = 'acceptance-temp-rule'; metric = 'exit_rate'; operatorCmp = '>='; thresholdValue = 0.09; trafficType = 5; enabled = 1; remark = 'auto acceptance, deleted afterwards' } | ConvertTo-Json
$rc = Invoke-RestMethod "$B/api/m2/rule" -Method Post -Body $ruleBody -ContentType 'application/json; charset=utf-8'
$rid = $rc.data.ruleId
if ($rc.code -eq 200 -and $rid -gt 0) { Write-Host "PASS create rule id=$rid" } else { $script:fail++; Write-Host "FAIL create rule" }

$updRule = @{ ruleName = 'acceptance-temp-rule-updated'; metric = 'page_values'; operatorCmp = '<='; thresholdValue = 3.5; enabled = 1; remark = 'updated' } | ConvertTo-Json
$ru = Invoke-RestMethod "$B/api/m2/rule/$rid" -Method Put -Body $updRule -ContentType 'application/json; charset=utf-8'
if ($ru.code -eq 200 -and $ru.data.ruleName -eq 'acceptance-temp-rule-updated' -and $ru.data.metric -eq 'page_values') {
    Write-Host "PASS update rule"
} else { $script:fail++; Write-Host "FAIL update rule" }

$t1 = Invoke-RestMethod "$B/api/m2/rule/$rid/toggle" -Method Put
$t2 = Invoke-RestMethod "$B/api/m2/rule/$rid/toggle" -Method Put
if ($t1.data.enabled -eq 0 -and $t2.data.enabled -eq 1) { Write-Host "PASS toggle enabled (1->0->1)" } else { $script:fail++; Write-Host "FAIL toggle" }

$kw = Invoke-RestMethod "$B/api/m2/rule/page?pageNum=1&pageSize=10&keyword=acceptance"
if ($kw.code -eq 200 -and $kw.data.total -ge 1) { Write-Host "PASS rule keyword paging total=$($kw.data.total)" } else { $script:fail++; Write-Host "FAIL rule keyword paging" }

$rd = Invoke-RestMethod "$B/api/m2/rule/$rid" -Method Delete
if ($rd.code -eq 200 -and $rd.data -eq $true) { Write-Host "PASS delete rule" } else { $script:fail++; Write-Host "FAIL delete rule" }

$badRule = @{ ruleName = 'bad'; metric = 'not_a_metric'; operatorCmp = '>'; thresholdValue = 1 } | ConvertTo-Json
$bv = Invoke-RestMethod "$B/api/m2/rule" -Method Post -Body $badRule -ContentType 'application/json; charset=utf-8'
if ($bv.code -eq 500) { Write-Host "PASS invalid metric rejected with code=500" } else { $script:fail++; Write-Host "FAIL invalid metric not rejected" }

Write-Host ""
Write-Host "===== 7. static resources and CORS =====" -ForegroundColor Cyan
foreach ($path in @('/dashboard-a/', '/dashboard-b/')) {
    try {
        $r = Invoke-WebRequest "$B$path" -TimeoutSec 10
        if ($r.StatusCode -eq 200 -and $r.Content.Length -gt 200) { Write-Host "PASS static page $path ($($r.Content.Length) B)" } else { $script:fail++; Write-Host "FAIL $path" }
    }
    catch { $script:fail++; Write-Host "FAIL $path -> $($_.Exception.Message)" }
}
try {
    $r = Invoke-WebRequest "$B/api/m1/overview" -Method Options -Headers @{ Origin = 'http://localhost:5500'; 'Access-Control-Request-Method' = 'GET' } -TimeoutSec 10
    if ($r.Headers['Access-Control-Allow-Origin']) { Write-Host "PASS CORS preflight ACAO=$($r.Headers['Access-Control-Allow-Origin'])" } else { $script:fail++; Write-Host "FAIL CORS preflight" }
}
catch { $script:fail++; Write-Host "FAIL CORS -> $($_.Exception.Message)" }

Write-Host ""
Write-Host "===== 8. data baseline check =====" -ForegroundColor Cyan
$h = Invoke-RestMethod "$B/api/common/health"
$rl = Invoke-RestMethod "$B/api/m2/rule/list"
if ($h.data.rows -eq 12205) { Write-Host "PASS session table back to baseline rows=12205" } else { $script:fail++; Write-Host "FAIL session rows=$($h.data.rows), expected 12205 (leftover test data?)" }
if ($rl.data.Count -eq 5) { Write-Host "PASS rule table back to baseline count=5" } else { $script:fail++; Write-Host "FAIL rule count=$($rl.data.Count), expected 5" }

Write-Host ""
if ($script:fail -eq 0) {
    Write-Host "===== ALL CHECKS PASSED (0 failures) =====" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "===== $script:fail CHECK(S) FAILED =====" -ForegroundColor Red
    exit 1
}
