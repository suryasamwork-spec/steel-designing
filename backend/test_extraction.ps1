$boundary = "---------------------------" + (Get-Date).Ticks.ToString("x")
$pdfPath = "d:\sd\backend\dummypdf.pdf"

# Create a dummy PDF if it doesn't exist
if (-not (Test-Path $pdfPath)) {
    Set-Content -Path $pdfPath -Value "Dummy PDF Content"
}

# Construct the body
$body = @"
--$boundary
Content-Disposition: form-data; name="pdf"; filename="dummypdf.pdf"
Content-Type: application/pdf

$(Get-Content $pdfPath -Raw)
--$boundary
Content-Disposition: form-data; name="x"

100
--$boundary
Content-Disposition: form-data; name="y"

100
--$boundary
Content-Disposition: form-data; name="width"

200
--$boundary
Content-Disposition: form-data; name="height"

100
--$boundary
Content-Disposition: form-data; name="page_num"

0
--$boundary--
"@

try {
    Invoke-RestMethod -Uri "http://localhost:5001/api/extract-text" `
        -Method Post `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Body $body `
        -ErrorAction Stop
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.ReadToEnd()
    }
}
