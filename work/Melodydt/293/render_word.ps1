$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\Study_material\Study_material\LLMHardwareDesign'
$wordInstance = New-Object -ComObject Word.Application
try {
    $wordInstance.Visible = $false
    $wordInstance.DisplayAlerts = 0
    $wordInstance.AutomationSecurity = 3
    $wordDoc = $wordInstance.Documents.Open("$taskRoot\output\docx\seven-model-200mhz-dac-table.docx", $false, $true)
    try { $wordDoc.ExportAsFixedFormat("$taskRoot\work\Melodydt\293\qa\word-table.pdf",17) }
    finally { $wordDoc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordDoc) }
} finally { $wordInstance.Quit(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordInstance) }
