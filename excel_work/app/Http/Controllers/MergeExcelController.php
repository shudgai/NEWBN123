<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use PhpOffice\PhpSpreadsheet\Style\Alignment;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Style\Font;
use PhpOffice\PhpSpreadsheet\Style\Border;

class MergeExcelController extends Controller
{
    public function index()
    {
        return view('merge_excel');
    }

    public function merge(Request $request)
    {
        $request->validate([
            'files'   => 'required|array|min:1',
            'files.*' => 'required|file',
            'mode'    => 'required|in:single,multi',
        ]);

        $files  = $request->file('files');
        $mode   = $request->input('mode', 'single');
        $skipHeader = $request->boolean('skip_header', true);

        $mergedSpreadsheet = new Spreadsheet();

        if ($mode === 'single') {
            // ── 模式一：所有資料合併到同一個 Sheet ──────────────────
            $activeSheet = $mergedSpreadsheet->getActiveSheet();
            $activeSheet->setTitle('合併資料');
            $currentRow  = 1;
            $isFirstFile = true;
            
            $feeKeywords = ['金額', '報價', '運費', '卡車費', '堆高機', '拆板回收', '代墊款'];
            $feeColumns = []; // Format: ['C' => ['index' => 3, 'total' => 0]]
            $globalLastSeenDate = '';
            $allCollectedRows = [];

            foreach ($files as $file) {
                try {
                    $spreadsheet = IOFactory::load($file->getPathname());
                } catch (\Exception $e) {
                    continue;
                }

                foreach ($spreadsheet->getAllSheets() as $sheet) {
                    $highestRow    = $sheet->getHighestDataRow();
                    $highestColumn = $sheet->getHighestDataColumn();

                    if ($highestRow < 1) continue;
                    
                    $highestColIndex = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString($highestColumn);

                    // Find Header Row (the row with column titles like 日期, 金額, 備註)
                    $headerRow = 1;
                    for ($r = 1; $r <= min(10, $highestRow); $r++) {
                        $rowStr = '';
                        for ($c = 1; $c <= min(10, $highestColIndex); $c++) {
                            $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $rowStr .= (string)$sheet->getCell($colStr . $r)->getValue();
                        }
                        if (str_contains($rowStr, '日期') || str_contains($rowStr, '客戶名稱')) {
                            $headerRow = $r;
                            break;
                        }
                    }

                    // Identify columns for this file
                    $dateColString = null;
                    $clientNameColString = null;
                    $currentFileRemarkColString = null;
                    for ($c = 1; $c <= $highestColIndex; $c++) {
                        $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                        $headerVal = trim((string)$sheet->getCell($colStr . $headerRow)->getValue());
                        if ($dateColString === null && (str_contains($headerVal, '日期'))) {
                            $dateColString = $colStr;
                        }
                        if ($clientNameColString === null && str_contains($headerVal, '客戶名稱')) {
                            $clientNameColString = $colStr;
                        }
                        if ($currentFileRemarkColString === null && str_contains($headerVal, '備註')) {
                            $currentFileRemarkColString = $colStr;
                        }
                    }

                    // Extract title date (e.g. "114年02月" or "115年4月1日")
                    $titleDate = '';
                    for ($r = 1; $r < $headerRow; $r++) {
                        for ($c = 1; $c <= $highestColIndex; $c++) {
                            $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $val = trim((string)$sheet->getCell($colStr . $r)->getFormattedValue());
                            if (preg_match('/(\d+\s*年\s*\d+\s*月(?:\s*\d+\s*[日號])?)/', $val, $matches)) {
                                $titleDate = str_replace(' ', '', $matches[1]);
                                break 2;
                            }
                        }
                    }
                    
                    $forceDateColumn = ($dateColString === null);

                    // If this is the first file, identify fee columns, copy headers, and set up sheet
                    if ($isFirstFile) {
                        $activeSheet->setShowGridlines(false); // Hide default gridlines
                        $globalForceDateColumn = $forceDateColumn;

                        $validHeaderCols = [];
                        for ($c = 1; $c <= $highestColIndex; $c++) {
                            $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $headerVal = (string)$sheet->getCell($colStr . $headerRow)->getValue();
                            
                            if (trim($headerVal) !== '') {
                                $validHeaderCols[] = $colStr;
                            }

                            foreach ($feeKeywords as $keyword) {
                                if (str_contains($headerVal, $keyword)) {
                                    $destColIndex = $c;
                                    if ($globalForceDateColumn) $destColIndex++;
                                    $destColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($destColIndex);
                                    
                                    $feeColumns[$destColStr] = [
                                        'index' => $destColIndex,
                                        'total' => 0,
                                        'srcCol' => $colStr
                                    ];
                                    break;
                                }
                            }
                        }

                        // Copy from row 1 to headerRow, only for valid columns
                        for ($r = 1; $r <= $headerRow; $r++) {
                            if ($r === $headerRow && $globalForceDateColumn) {
                                $activeSheet->getCell('A' . $currentRow)->setValue('日期');
                                $style = $activeSheet->getStyle('A' . $currentRow);
                                $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                            }

                            foreach ($validHeaderCols as $colStr) {
                                $cell = $sheet->getCell($colStr . $r);
                                $destColStr = $colStr;
                                if ($globalForceDateColumn) {
                                    $destColIndex = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString($colStr) + 1;
                                    $destColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($destColIndex);
                                }
                                $activeSheet->getCell($destColStr . $currentRow)->setValue($cell->getValue());
                                
                                $style = $activeSheet->getStyle($destColStr . $currentRow);
                                $style->getFont()->setName('微軟正黑體')->setSize(12);
                                if ($r === $headerRow) {
                                    $style->getFont()->setBold(true);
                                }
                            }
                            $currentRow++;
                        }
                        
                        $maxDataColIndex = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString(end($validHeaderCols));
                        if ($globalForceDateColumn) $maxDataColIndex++;
                        $isFirstFile = false;
                    }

                    // Extract header row strings to detect repeated headers later
                    $headerRowStrings = [];
                    for ($r = 1; $r <= $headerRow; $r++) {
                        $str = '';
                        for ($c = 1; $c <= $highestColIndex; $c++) {
                            $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $str .= trim((string)$sheet->getCell($colStr . $r)->getFormattedValue());
                        }
                        $cleanStr = str_replace(' ', '', $str);
                        if (strlen($cleanStr) > 2) {
                            $headerRowStrings[] = $cleanStr;
                        }
                    }

                    // Data starts after header row
                    $startRow = $headerRow + 1;

                    for ($row = $startRow; $row <= $highestRow; $row++) {
                        // 1. Extract Date first so we don't lose it if we skip the row
                        $rowDate = '';
                        if ($dateColString) {
                            $cell = $sheet->getCell($dateColString . $row);
                            $cellDateVal = '';
                            if (\PhpOffice\PhpSpreadsheet\Shared\Date::isDateTime($cell)) {
                                try {
                                    $dateObj = \PhpOffice\PhpSpreadsheet\Shared\Date::excelToDateTimeObject($cell->getValue());
                                    $cellDateVal = $dateObj->format('m/d');
                                } catch (\Exception $e) {
                                    $cellDateVal = trim((string)$cell->getFormattedValue());
                                }
                            } else {
                                $cellDateVal = trim((string)$cell->getFormattedValue());
                                // Try to manually parse string dates if they are not Excel Date objects
                                if (preg_match('/(\d+)\s*月\s*(\d+)\s*[日號]?/', $cellDateVal, $m) || preg_match('/(?:^|[^\d])(\d+)\/(\d+)(?:[^\d]|$)/', $cellDateVal, $m)) {
                                    $month = str_pad($m[1], 2, '0', STR_PAD_LEFT);
                                    $day = str_pad($m[2], 2, '0', STR_PAD_LEFT);
                                    $cellDateVal = "$month/$day";
                                }
                            }

                            if ($cellDateVal !== '') {
                                $globalLastSeenDate = $cellDateVal;
                            }
                        }
                        $rowDate = $globalLastSeenDate;

                        // 2. Check if row has any actual data (excluding the date column) and isn't a total row
                        $hasData = false;
                        $isTotalRow = false;
                        $hasFeeData = false;
                        $hasNonZeroNonFeeData = false;
                        $limitCol = isset($maxDataColIndex) ? $maxDataColIndex : $highestColIndex;
                        
                        $rowStrClean = '';
                        for ($c = 1; $c <= $limitCol; $c++) {
                            $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $cellVal = trim((string)$sheet->getCell($colStr . $row)->getFormattedValue());
                            $rowStrClean .= $cellVal;
                            
                            // If it's not the date column and it's not empty, we have data
                            if ($colStr !== $dateColString && $cellVal !== '') {
                                $hasData = true;
                            }
                            
                            if (str_contains($cellVal, '總計') || str_contains($cellVal, '合計') || str_contains($cellVal, '總額') || str_contains($cellVal, '總金額') || str_contains($cellVal, '小計')) {
                                $isTotalRow = true;
                            }
                            
                            // Calculate destination column string for fee lookup
                            $destColStr = $colStr;
                            if (isset($globalForceDateColumn) && $globalForceDateColumn) {
                                $destColIndex = $c + 1;
                                $destColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($destColIndex);
                            }
                            
                            if (isset($feeColumns[$destColStr]) && $cellVal !== '') {
                                $cleanVal = str_replace(',', '', $cellVal);
                                if (is_numeric($cleanVal)) {
                                    $hasFeeData = true;
                                }
                            } elseif ($cellVal !== '' && $cellVal !== '0' && $cellVal !== '0.0' && $cellVal !== '0.00' && $cellVal !== '0.000' && $cellVal !== '-') {
                                // This is a non-fee column that has a meaningful (non-zero) value
                                $hasNonZeroNonFeeData = true;
                            }
                        }
                        
                        if ($hasFeeData && !$hasNonZeroNonFeeData) {
                            $isTotalRow = true;
                        }
                        
                        $rowStrClean = str_replace(' ', '', $rowStrClean);
                        
                        // Check if it's a structural metadata row (repeated headers within same sheet)
                        $isMetadataRow = false;
                        if (!$hasFeeData && $rowStrClean !== '') {
                            foreach ($headerRowStrings as $hs) {
                                if ($hs === $rowStrClean) {
                                    $isMetadataRow = true;
                                    break;
                                }
                            }
                            if (!$isMetadataRow) {
                                if (
                                    str_contains($rowStrClean, '有限公司') || 
                                    str_contains($rowStrClean, '明細表') || 
                                    (str_contains($rowStrClean, '日期') && str_contains($rowStrClean, '客戶名稱')) ||
                                    str_contains($rowStrClean, '請款明細')
                                ) {
                                    $isMetadataRow = true;
                                }
                            }
                        }

                        if ($isMetadataRow) {
                            $globalLastSeenDate = ''; // Reset date for the new section
                            // Update title date if this metadata row has one
                            if (preg_match('/(\d+\s*年\s*\d+\s*月(?:\s*\d+\s*[日號])?)/', $rowStrClean, $matches)) {
                                $titleDate = str_replace(' ', '', $matches[1]);
                            }
                            continue;
                        }

                        // Skip if it only contains a date (no other data) or if it's a total row
                        if (!$hasData || $isTotalRow) {
                            continue;
                        }

                        // Figure out final date string
                        $finalDateStr = '';
                        if (isset($globalForceDateColumn) && $globalForceDateColumn) {
                            $finalDateStr = $titleDate;
                        } else {
                            $finalDateStr = $rowDate;
                        }

                        // Format as mm/dd
                        if (preg_match('/(\d+)\s*月\s*(\d+)\s*[日號]?/', $finalDateStr, $m) || preg_match('/(?:^|[^\d])(\d+)\/(\d+)(?:[^\d]|$)/', $finalDateStr, $m)) {
                            $month = str_pad($m[1], 2, '0', STR_PAD_LEFT);
                            $day = str_pad($m[2], 2, '0', STR_PAD_LEFT);
                            $finalDateStr = "$month/$day";
                        } elseif (preg_match('/(\d+)\s*月/', $finalDateStr, $m)) {
                            $month = str_pad($m[1], 2, '0', STR_PAD_LEFT);
                            $finalDateStr = "$month";
                        }

                        // 3. Collect the row instead of outputting immediately
                        $rowDataForSorting = [
                            'sort_date' => $finalDateStr,
                            'original_index' => count($allCollectedRows),
                            'cells' => []
                        ];

                        for ($c = 1; $c <= $limitCol; $c++) {
                            $srcColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $destColStr = $srcColStr;
                            if (isset($globalForceDateColumn) && $globalForceDateColumn) {
                                $destColIndex = $c + 1;
                                $destColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($destColIndex);
                            }

                            $cell = $sheet->getCell($srcColStr . $row);
                            
                            if (isset($feeColumns[$destColStr])) {
                                $cellValue = $cell->getValue();
                                $rowDataForSorting['cells'][$destColStr] = [
                                    'value' => $cellValue,
                                    'is_fee' => true
                                ];
                                if (is_numeric($cellValue)) {
                                    $feeColumns[$destColStr]['total'] += floatval($cellValue);
                                } else {
                                    $val = floatval(str_replace(',', '', (string)$cellValue));
                                    $feeColumns[$destColStr]['total'] += $val;
                                }
                            } else {
                                $formattedValue = (string)$cell->getFormattedValue();
                                
                                // Fill in the blank date column
                                if ($srcColStr === $dateColString) {
                                    $formattedValue = $finalDateStr;
                                }
                                
                                // Remove "P2" from remark
                                if ($srcColStr === $currentFileRemarkColString) {
                                    $formattedValue = str_replace('P2', '', $formattedValue);
                                }
                                
                                $rowDataForSorting['cells'][$destColStr] = [
                                    'value' => $formattedValue,
                                    'is_fee' => false
                                ];
                            }
                        }
                        $allCollectedRows[] = $rowDataForSorting;
                    }
                }
            }
            
            // --- Sort and Output rows ---
            usort($allCollectedRows, function($a, $b) {
                $cmp = strcmp($a['sort_date'], $b['sort_date']);
                if ($cmp === 0) {
                    return $a['original_index'] <=> $b['original_index'];
                }
                return $cmp;
            });

            foreach ($allCollectedRows as $rowData) {
                if (isset($globalForceDateColumn) && $globalForceDateColumn) {
                    $activeSheet->getCell('A' . $currentRow)->setValueExplicit($rowData['sort_date'], \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
                    $style = $activeSheet->getStyle('A' . $currentRow);
                    $style->getFont()->setName('微軟正黑體')->setSize(12);
                }

                foreach ($rowData['cells'] as $destColStr => $cellData) {
                    if ($cellData['is_fee']) {
                        $activeSheet->getCell($destColStr . $currentRow)->setValue($cellData['value']);
                    } else {
                        $activeSheet->getCell($destColStr . $currentRow)->setValueExplicit($cellData['value'], \PhpOffice\PhpSpreadsheet\Cell\DataType::TYPE_STRING);
                    }
                    
                    $style = $activeSheet->getStyle($destColStr . $currentRow);
                    $style->getFont()->setName('微軟正黑體')->setSize(12);
                }
                $currentRow++;
            }
            
            // Append Grand Total Row at the end
            if (!empty($feeColumns)) {
                $minFeeColIndex = min(array_column($feeColumns, 'index'));
                $labelColStr = $minFeeColIndex > 1 
                    ? \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($minFeeColIndex - 1) 
                    : 'A';
                    
                $activeSheet->getCell($labelColStr . $currentRow)->setValue('總金額');
                $style = $activeSheet->getStyle($labelColStr . $currentRow);
                $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                $style->getAlignment()->setHorizontal(Alignment::HORIZONTAL_RIGHT);
                
                foreach ($feeColumns as $colStr => $feeData) {
                    $activeSheet->getCell($colStr . $currentRow)->setValue($feeData['total']);
                    $style = $activeSheet->getStyle($colStr . $currentRow);
                    $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                    $style->getNumberFormat()->setFormatCode('#,##0');
                }
            }

            // Auto-size columns
            $col = 'A';
            $highestCol = $activeSheet->getHighestDataColumn();
            while ($col <= $highestCol) {
                $activeSheet->getColumnDimension($col)->setAutoSize(true);
                if ($col === $highestCol) break;
                $col++;
            }

        } else {
            // ── 模式二：每個檔案一個 Sheet ───────────────────────────
            $sheetIndex = 0;

            foreach ($files as $file) {
                try {
                    $spreadsheet = IOFactory::load($file->getPathname());
                } catch (\Exception $e) {
                    continue;
                }

                $sourceSheet   = $spreadsheet->getActiveSheet();
                $highestRow    = $sourceSheet->getHighestDataRow();
                $highestColumn = $sourceSheet->getHighestDataColumn();

                if ($sheetIndex === 0) {
                    $targetSheet = $mergedSpreadsheet->getActiveSheet();
                } else {
                    $targetSheet = $mergedSpreadsheet->createSheet();
                }

                // Sheet 名稱取自檔名（Excel 限制 31 字元）
                $sheetName = pathinfo($file->getClientOriginalName(), PATHINFO_FILENAME);
                $sheetName = mb_substr($sheetName, 0, 31);
                try {
                    $targetSheet->setTitle($sheetName);
                } catch (\Exception $e) {
                    $targetSheet->setTitle('Sheet' . ($sheetIndex + 1));
                }

                // Copy data & styles
                $col = 'A';
                while ($col <= $highestColumn) {
                    for ($row = 1; $row <= $highestRow; $row++) {
                        $cellValue = $sourceSheet->getCell($col . $row)->getValue();
                        $targetSheet->getCell($col . $row)->setValue($cellValue);
                        $sourceStyle = $sourceSheet->getStyle($col . $row);
                        $targetSheet->duplicateStyle($sourceStyle, $col . $row);
                    }
                    $targetSheet->getColumnDimension($col)->setAutoSize(true);
                    if ($col === $highestColumn) break;
                    $col++;
                }

                $sheetIndex++;
            }
        }

        // ── 寫出並回傳 ─────────────────────────────────────────────
        $filename = '合併報表_' . now()->format('YmdHis') . '.xlsx';
        $tempDir  = storage_path('app/temp');

        if (!file_exists($tempDir)) {
            mkdir($tempDir, 0755, true);
        }

        $tempPath = $tempDir . '/' . $filename;
        $writer   = new Xlsx($mergedSpreadsheet);
        $writer->save($tempPath);

        return response()->download($tempPath, $filename)->deleteFileAfterSend(true);
    }
}
