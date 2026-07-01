param(
    [Parameter(Mandatory=$true)]
    [string]$InputDoc,
    [Parameter(Mandatory=$true)]
    [string]$OutputDoc
)

$ErrorActionPreference = "Stop"

$wdSectionBreakNextPage = 2
$wdSectionBreakContinuous = 3
$wdHeaderFooterPrimary = 1
$wdAlignPageNumberCenter = 1
$wdPageNumberStyleArabic = 0
$wdPageNumberStyleUppercaseRoman = 1
$wdFieldEmpty = -1

$abstractCompact = ([string][char]25688) + ([string][char]35201)
$tocCompact = ([string][char]30446) + ([string][char]24405)
$bodyNeedles = @(
    (([string][char]39033) + ([string][char]30446)),
    (([string][char]25104) + ([string][char]21592))
)

Copy-Item -LiteralPath $InputDoc -Destination $OutputDoc -Force

$word = $null
try {
    $step = "open word"
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($OutputDoc)

    function NormalizeText($s) {
        return (($s -replace "`r", "") -replace "`a", "").Trim()
    }

    function CompactText($s) {
        return ((NormalizeText $s) -replace "\s", "")
    }

    function FindParagraphIndexByText($document, [scriptblock]$predicate, [int]$startIndex = 1) {
        for ($i = $startIndex; $i -le $document.Paragraphs.Count; $i++) {
            $p = $document.Paragraphs.Item($i)
            $text = NormalizeText $p.Range.Text
            $compact = CompactText $p.Range.Text
            if (& $predicate $text $compact $p) {
                return $i
            }
        }
        throw "Paragraph not found."
    }

    $step = "find anchors"
    $abstractIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $abstractCompact }
    $tocIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $tocCompact } $abstractIdx
    $bodyIdx = FindParagraphIndexByText $doc {
        param($text, $compact, $p)
        ($compact.StartsWith("1") -and $compact.Contains($bodyNeedles[0]) -and $compact.Contains($bodyNeedles[1])) -and
            ($p.OutlineLevel -eq 1)
    } $tocIdx

    $tocPara = $doc.Paragraphs.Item($tocIdx)
    $bodyPara = $doc.Paragraphs.Item($bodyIdx)

    # Keep the visible TOC title out of the generated TOC.
    $step = "format toc title"
    $tocPara.Style = $doc.Styles.Item(-1)
    $tocPara.Range.ParagraphFormat.Alignment = 1
    $tocPara.Range.Font.Name = "Times New Roman"
    $tocPara.Range.Font.NameFarEast = "Microsoft JhengHei UI"
    $tocPara.Range.Font.Size = 18
    $tocPara.Range.Font.Bold = $true

    # Remove old static/manual TOC entries between the title and chapter 1.
    $step = "delete old toc"
    $deleteRange = $doc.Range($tocPara.Range.End, $bodyPara.Range.Start)
    $deleteRange.Delete() | Out-Null

    $step = "refind body"
    $bodyIdx = FindParagraphIndexByText $doc {
        param($text, $compact, $p)
        ($compact.StartsWith("1") -and $compact.Contains($bodyNeedles[0]) -and $compact.Contains($bodyNeedles[1])) -and
            ($p.OutlineLevel -eq 1)
    } $tocIdx
    $bodyPara = $doc.Paragraphs.Item($bodyIdx)

    # The reference report keeps the whole TOC page in a two-column section.
    $step = "split toc section"
    $beforeToc = $doc.Range($tocPara.Range.Start, $tocPara.Range.Start)
    $beforeToc.InsertBreak($wdSectionBreakContinuous)

    $tocIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $tocCompact } $abstractIdx
    $tocPara = $doc.Paragraphs.Item($tocIdx)

    $step = "insert toc field"
    $tocFieldRange = $doc.Range($tocPara.Range.End, $tocPara.Range.End)
    $tocFieldRange.InsertParagraphAfter()
    $tocFieldRange = $doc.Range($tocPara.Range.End, $tocPara.Range.End)
    $field = $doc.Fields.Add($tocFieldRange, $wdFieldEmpty, 'TOC \o "1-3" \h \z \u', $true)
    $field.Update() | Out-Null

    $step = "insert body break"
    $bodyIdx = FindParagraphIndexByText $doc {
        param($text, $compact, $p)
        ($compact.StartsWith("1") -and $compact.Contains($bodyNeedles[0]) -and $compact.Contains($bodyNeedles[1])) -and
            ($p.OutlineLevel -eq 1)
    } $tocIdx
    $bodyPara = $doc.Paragraphs.Item($bodyIdx)
    $beforeBody = $doc.Range($bodyPara.Range.Start, $bodyPara.Range.Start)
    $beforeBody.InsertBreak($wdSectionBreakNextPage)

    # Make the abstract start a front-matter section if it is still joined to the cover.
    $step = "insert abstract break"
    $abstractIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $abstractCompact }
    $abstractPara = $doc.Paragraphs.Item($abstractIdx)
    if ($abstractPara.Range.Sections.Item(1).Index -eq 1) {
        $beforeAbstract = $doc.Range($abstractPara.Range.Start, $abstractPara.Range.Start)
        $beforeAbstract.InsertBreak($wdSectionBreakContinuous)
    }

    $step = "refind sections"
    $abstractIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $abstractCompact }
    $tocIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $tocCompact } $abstractIdx
    $bodyIdx = FindParagraphIndexByText $doc {
        param($text, $compact, $p)
        ($compact.StartsWith("1") -and $compact.Contains($bodyNeedles[0]) -and $compact.Contains($bodyNeedles[1])) -and
            ($p.OutlineLevel -eq 1)
    } $tocIdx

    $abstractSectionIndex = $doc.Paragraphs.Item($abstractIdx).Range.Sections.Item(1).Index
    $tocSectionIndex = $doc.Paragraphs.Item($tocIdx).Range.Sections.Item(1).Index
    $bodySectionIndex = $doc.Paragraphs.Item($bodyIdx).Range.Sections.Item(1).Index

    $step = "set columns"
    for ($i = 1; $i -le $doc.Sections.Count; $i++) {
        $doc.Sections.Item($i).PageSetup.TextColumns.SetCount(1)
    }
    if ($tocSectionIndex -ge 1) {
        $doc.Sections.Item($tocSectionIndex).PageSetup.TextColumns.SetCount(2)
        $doc.Sections.Item($tocSectionIndex).PageSetup.TextColumns.EvenlySpaced = $true
    }

    $step = "clear footers"
    for ($i = 1; $i -le $doc.Sections.Count; $i++) {
        $section = $doc.Sections.Item($i)
        $footer = $section.Footers.Item($wdHeaderFooterPrimary)
        $footer.LinkToPrevious = $false
        $footer.Range.Text = ""
        $footer.Range.ParagraphFormat.Alignment = 1
        $section.PageSetup.DifferentFirstPageHeaderFooter = $false
    }

    $step = "front page numbers"
    for ($i = $abstractSectionIndex; $i -lt $bodySectionIndex; $i++) {
        $section = $doc.Sections.Item($i)
        $footer = $section.Footers.Item($wdHeaderFooterPrimary)
        $footer.PageNumbers.NumberStyle = $wdPageNumberStyleUppercaseRoman
        if ($i -eq $abstractSectionIndex) {
            $footer.PageNumbers.RestartNumberingAtSection = $true
            $footer.PageNumbers.StartingNumber = 1
        } else {
            $footer.PageNumbers.RestartNumberingAtSection = $false
        }
        $footer.PageNumbers.Add($wdAlignPageNumberCenter, $true) | Out-Null
    }

    $step = "body page numbers"
    for ($i = $bodySectionIndex; $i -le $doc.Sections.Count; $i++) {
        $section = $doc.Sections.Item($i)
        $footer = $section.Footers.Item($wdHeaderFooterPrimary)
        $footer.PageNumbers.NumberStyle = $wdPageNumberStyleArabic
        if ($i -eq $bodySectionIndex) {
            $footer.PageNumbers.RestartNumberingAtSection = $true
            $footer.PageNumbers.StartingNumber = 1
        } else {
            $footer.PageNumbers.RestartNumberingAtSection = $false
        }
        $footer.PageNumbers.Add($wdAlignPageNumberCenter, $true) | Out-Null
    }

    $step = "update fields"
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) {
        $toc.Update() | Out-Null
        $toc.UpdatePageNumbers() | Out-Null
    }

    $step = "final columns"
    $tocIdx = FindParagraphIndexByText $doc { param($text, $compact, $p) $compact -eq $tocCompact } $abstractIdx
    $bodyIdx = FindParagraphIndexByText $doc {
        param($text, $compact, $p)
        ($compact.StartsWith("1") -and $compact.Contains($bodyNeedles[0]) -and $compact.Contains($bodyNeedles[1])) -and
            ($p.OutlineLevel -eq 1)
    } $tocIdx
    $tocSectionIndex = $doc.Paragraphs.Item($tocIdx).Range.Sections.Item(1).Index
    $bodySectionIndex = $doc.Paragraphs.Item($bodyIdx).Range.Sections.Item(1).Index
    for ($i = 1; $i -le $doc.Sections.Count; $i++) {
        $doc.Sections.Item($i).PageSetup.TextColumns.SetCount(1)
    }
    $doc.Sections.Item($tocSectionIndex).PageSetup.TextColumns.SetCount(2)
    $doc.Sections.Item($tocSectionIndex).PageSetup.TextColumns.EvenlySpaced = $true

    $step = "save"
    $doc.Save()
    $doc.Close($false)
    Write-Output $OutputDoc
}
catch {
    Write-Error ("Failed at step: " + $step + ". " + $_.Exception.Message)
    throw
}
finally {
    if ($word -ne $null) {
        $word.Quit()
    }
}
