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
            'files'   => 'nullable|array',
            'files.*' => 'file',
            'temp_files' => 'nullable|array',
            'mode'    => 'required|in:single,multi',
        ]);

        $mode   = $request->input('mode', 'single');
        $skipHeader = $request->boolean('skip_header', true);
        $action = $request->input('action', 'download'); // 'download' or 'save'

        $tempFiles = $request->input('temp_files', []);
        $files = [];

        if ($request->hasFile('files')) {
            $files = $request->file('files');
        } elseif (!empty($tempFiles)) {
            foreach ($tempFiles as $tempFile) {
                $tempFile = basename($tempFile);
                $filePath = storage_path('app/temp/' . $tempFile);
                if (file_exists($filePath)) {
                    $files[] = new class($filePath, $tempFile) {
                        private $path;
                        private $originalName;
                        public function __construct($path, $tempName) {
                            $this->path = $path;
                            $parts = explode('_', $tempName, 3);
                            $this->originalName = isset($parts[2]) ? $parts[2] : $tempName;
                        }
                        public function getPathname() {
                            return $this->path;
                        }
                        public function getClientOriginalName() {
                            return $this->originalName;
                        }
                    };
                }
            }
        }

        if (empty($files)) {
            return response()->json(['message' => 'No files provided for merging.'], 400);
        }

        $mergedSpreadsheet = new Spreadsheet();

        if ($mode === 'single') {
            // ── 模式一：所有資料合併到同一個 Sheet ──────────────────
            $feeKeywords = ['金額', '報價', '運費', '卡車費', '堆高機', '拆板回收', '代墊款'];
            $predefinedOrder = [
                '日期'=>1, '客戶名稱'=>2, '主併提單號碼'=>3, '送貨地點'=>4, '件數'=>5, '重量(kg)'=>6, '噸位'=>7, 
                '卡車費'=>8, '堆高機'=>9, '拆板回收'=>10, '代墊款'=>11, '報價'=>12, '運費'=>13, '金額'=>14, '備註'=>99
            ];
            
            $globalLastSeenDate = '';
            $allCollectedRows = [];
            
            $globalHeaders = []; 
            $globalHeaderOriginal = []; 
            
            $firstFileHeaderBlock = [];
            $firstFileForceDate = false;
            
            $isFirstFile = true;

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

                    // Find Header Row
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

                    if ($isFirstFile) {
                        $firstFileForceDate = $forceDateColumn;
                        if ($forceDateColumn) {
                            $globalHeaders[] = '日期';
                            $globalHeaderOriginal['日期'] = '日期';
                        }
                    }

                    $currentSheetHeaderMap = []; // srcCol => cleanHeaderVal
                    $isFeeColCache = [];
                    for ($c = 1; $c <= $highestColIndex; $c++) {
                        $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                        $headerVal = trim((string)$sheet->getCell($colStr . $headerRow)->getValue());
                        if ($headerVal === '' && $colStr === $dateColString) {
                            $headerVal = '日期';
                        }
                        
                        if ($headerVal !== '') {
                            $cleanHeaderVal = preg_replace('/[\p{Z}\s\r\n]+/u', '', $headerVal);
                            $currentSheetHeaderMap[$colStr] = $cleanHeaderVal;
                            
                            if (!in_array($cleanHeaderVal, $globalHeaders)) {
                                $globalHeaders[] = $cleanHeaderVal;
                                $globalHeaderOriginal[$cleanHeaderVal] = $headerVal;
                            }
                            
                            $isFee = false;
                            foreach ($feeKeywords as $keyword) {
                                if (str_contains($cleanHeaderVal, $keyword)) {
                                    $isFee = true;
                                    break;
                                }
                            }
                            $isFeeColCache[$colStr] = $isFee;
                        }
                    }
                    
                    if ($isFirstFile) {
                        for ($r = 1; $r <= $headerRow; $r++) {
                            $rowCells = [];
                            foreach ($currentSheetHeaderMap as $srcCol => $cleanVal) {
                                $rowCells[$cleanVal] = $sheet->getCell($srcCol . $r)->getValue();
                            }
                            $firstFileHeaderBlock[] = $rowCells;
                        }
                        $isFirstFile = false;
                    }

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

                    $startRow = $headerRow + 1;

                    for ($row = $startRow; $row <= $highestRow; $row++) {
                        $rowDate = '';
                        if ($dateColString) {
                            $cell = $sheet->getCell($dateColString . $row);
                            $cellDateVal = '';
                            if (\PhpOffice\PhpSpreadsheet\Shared\Date::isDateTime($cell)) {
                                try {
                                    $dateObj = \PhpOffice\PhpSpreadsheet\Shared\Date::excelToDateTimeObject($cell->getCalculatedValue());
                                    $cellDateVal = $dateObj->format('m/d');
                                } catch (\Exception $e) {
                                    $cellDateVal = trim((string)$cell->getFormattedValue());
                                }
                            } else {
                                $cellDateVal = trim((string)$cell->getFormattedValue());
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

                        $hasData = false;
                        $isTotalRow = false;
                        $hasFeeData = false;
                        $hasNonZeroNonFeeData = false;
                        
                        $rowStrClean_for_metadata = '';
                        for ($c = 1; $c <= $highestColIndex; $c++) {
                            $colStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            $cellVal = trim((string)$sheet->getCell($colStr . $row)->getFormattedValue());
                            $rowStrClean_for_metadata .= $cellVal;
                            
                            if (!isset($currentSheetHeaderMap[$colStr])) {
                                continue;
                            }
                            
                            if ($colStr !== $dateColString && $cellVal !== '') {
                                $hasData = true;
                            }
                            
                            if (str_contains($cellVal, '總計') || str_contains($cellVal, '合計') || str_contains($cellVal, '總額') || str_contains($cellVal, '總金額') || str_contains($cellVal, '小計')) {
                                $isTotalRow = true;
                            }
                            
                            if ($isFeeColCache[$colStr] && $cellVal !== '') {
                                $cleanVal = str_replace(',', '', $cellVal);
                                if (is_numeric($cleanVal)) {
                                    $hasFeeData = true;
                                }
                            } elseif ($cellVal !== '' && $cellVal !== '0' && $cellVal !== '0.0' && $cellVal !== '0.00' && $cellVal !== '0.000' && $cellVal !== '-') {
                                $hasNonZeroNonFeeData = true;
                            }
                        }
                        
                        if ($hasFeeData && !$hasNonZeroNonFeeData) {
                            $isTotalRow = true;
                        }
                        
                        $rowStrClean_for_metadata = str_replace(' ', '', $rowStrClean_for_metadata);
                        
                        $isMetadataRow = false;
                        if (!$hasFeeData && $rowStrClean_for_metadata !== '') {
                            foreach ($headerRowStrings as $hs) {
                                if ($hs === $rowStrClean_for_metadata) {
                                    $isMetadataRow = true;
                                    break;
                                }
                            }
                            if (!$isMetadataRow) {
                                if (
                                    str_contains($rowStrClean_for_metadata, '有限公司') || 
                                    str_contains($rowStrClean_for_metadata, '明細表') || 
                                    (str_contains($rowStrClean_for_metadata, '日期') && str_contains($rowStrClean_for_metadata, '客戶名稱')) ||
                                    str_contains($rowStrClean_for_metadata, '請款明細')
                                ) {
                                    $isMetadataRow = true;
                                }
                            }
                        }

                        if ($isMetadataRow) {
                            $globalLastSeenDate = ''; // Reset date for the new section
                            if (preg_match('/(\d+\s*年\s*\d+\s*月(?:\s*\d+\s*[日號])?)/', $rowStrClean_for_metadata, $matches)) {
                                $titleDate = str_replace(' ', '', $matches[1]);
                            }
                            continue;
                        }

                        if (!$hasData || $isTotalRow) {
                            continue;
                        }

                        $finalDateStr = '';
                        if ($dateColString === null) {
                            $finalDateStr = $titleDate;
                        } else {
                            $finalDateStr = $rowDate;
                        }

                        if (preg_match('/(\d+)\s*月\s*(\d+)\s*[日號]?/', $finalDateStr, $m) || preg_match('/(?:^|[^\d])(\d+)\/(\d+)(?:[^\d]|$)/', $finalDateStr, $m)) {
                            $month = str_pad($m[1], 2, '0', STR_PAD_LEFT);
                            $day = str_pad($m[2], 2, '0', STR_PAD_LEFT);
                            $finalDateStr = "$month/$day";
                        } elseif (preg_match('/(\d+)\s*月/', $finalDateStr, $m)) {
                            $month = str_pad($m[1], 2, '0', STR_PAD_LEFT);
                            $finalDateStr = "$month";
                        }

                        $rowDataForSorting = [
                            'sort_date' => $finalDateStr,
                            'original_index' => count($allCollectedRows),
                            'cells' => []
                        ];

                        if ($dateColString === null) {
                            $rowDataForSorting['cells']['日期'] = [
                                'value' => $finalDateStr,
                                'is_fee' => false
                            ];
                        }

                        for ($c = 1; $c <= $highestColIndex; $c++) {
                            $srcColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($c);
                            if (!isset($currentSheetHeaderMap[$srcColStr])) {
                                continue;
                            }
                            $cleanVal = $currentSheetHeaderMap[$srcColStr];
                            $cell = $sheet->getCell($srcColStr . $row);
                            
                            if ($isFeeColCache[$srcColStr]) {
                                try {
                                    $cellValue = $cell->getCalculatedValue();
                                } catch (\Exception $e) {
                                    $cellValue = $cell->getValue();
                                }
                                $rowDataForSorting['cells'][$cleanVal] = [
                                    'value' => $cellValue,
                                    'is_fee' => true
                                ];
                            } else {
                                $formattedValue = (string)$cell->getFormattedValue();
                                if ($srcColStr === $dateColString) {
                                    $formattedValue = $finalDateStr;
                                }
                                if ($srcColStr === $currentFileRemarkColString) {
                                    $formattedValue = str_replace('P2', '', $formattedValue);
                                }
                                $rowDataForSorting['cells'][$cleanVal] = [
                                    'value' => $formattedValue,
                                    'is_fee' => false
                                ];
                            }
                        }

                        // Apply special rule for 639: forklift fee is 0 if weight <= 100
                        $is639 = str_contains($file->getClientOriginalName(), '639') || str_contains($rowDataForSorting['cells']['客戶名稱']['value'] ?? '', '639');
                        if ($is639) {
                            $weightStr = $rowDataForSorting['cells']['重量(kg)']['value'] ?? '0';
                            $weight = (float)str_replace(',', '', (string)$weightStr);
                            if ($weight <= 100) {
                                if (isset($rowDataForSorting['cells']['堆高機'])) {
                                    $rowDataForSorting['cells']['堆高機']['value'] = 0;
                                }
                            }
                        }

                        $allCollectedRows[] = $rowDataForSorting;
                    }
                }
            }

            // --- Sort rows ---
            usort($allCollectedRows, function($a, $b) {
                $cmp = strcmp($a['sort_date'], $b['sort_date']);
                if ($cmp === 0) {
                    return $a['original_index'] <=> $b['original_index'];
                }
                return $cmp;
            });

            if ($action === 'save') {
                $savedCount = 0;
                $updatedCount = 0;
                foreach ($allCollectedRows as $rowData) {
                    $cells = $rowData['cells'];
                    
                    $date = $cells['日期']['value'] ?? null;
                    $clientName = $cells['客戶名稱']['value'] ?? null;
                    $billNo = $cells['主併提單號碼']['value'] ?? $cells['主倂提單號碼']['value'] ?? null;
                    $location = $cells['送貨地點']['value'] ?? null;
                    
                    if (empty($date) && empty($clientName) && empty($billNo)) {
                        continue;
                    }
                    
                    $pieces = (int)str_replace(',', '', $cells['件數']['value'] ?? '0');
                    $weight = (float)str_replace(',', '', $cells['重量(kg)']['value'] ?? '0');
                    $tonnage = (float)str_replace(',', '', $cells['噸位']['value'] ?? '0');
                    $truckFee = (int)str_replace(',', '', $cells['卡車費']['value'] ?? '0');
                    $forkliftFee = (int)str_replace(',', '', $cells['堆高機']['value'] ?? '0');
                    $palletRecoveryFee = (int)str_replace(',', '', $cells['拆板回收']['value'] ?? '0');
                    $remark = $cells['備註']['value'] ?? null;
                    
                    $existing = \App\Models\Waybill::where('date', $date)->where('bill_no', $billNo)->first();
                    if ($existing) {
                        $existing->update([
                            'client_name' => $clientName,
                            'location' => $location,
                            'pieces' => $pieces,
                            'weight' => $weight,
                            'tonnage' => $tonnage,
                            'truck_fee' => $truckFee,
                            'forklift_fee' => $forkliftFee,
                            'pallet_recovery_fee' => $palletRecoveryFee,
                            'remark' => $remark,
                        ]);
                        $updatedCount++;
                    } else {
                        \App\Models\Waybill::create([
                            'date' => $date,
                            'bill_no' => $billNo,
                            'client_name' => $clientName,
                            'location' => $location,
                            'pieces' => $pieces,
                            'weight' => $weight,
                            'tonnage' => $tonnage,
                            'truck_fee' => $truckFee,
                            'forklift_fee' => $forkliftFee,
                            'pallet_recovery_fee' => $palletRecoveryFee,
                            'remark' => $remark,
                        ]);
                        $savedCount++;
                    }
                }
                
                return response()->json([
                    'success' => true,
                    'message' => "成功新增 {$savedCount} 筆，更新 {$updatedCount} 筆資料！"
                ]);
            }

            // --- Write Setup ---
            $activeSheet = $mergedSpreadsheet->getActiveSheet();
            $activeSheet->setTitle('合併資料');
            $activeSheet->setShowGridlines(false);
            $currentRow = 1;

            $fixedColumns = [
                '日期' => 'A',
                '客戶名稱' => 'B',
                '主併提單號碼' => 'C',
                '主倂提單號碼' => 'C', // alias just in case
                '送貨地點' => 'D',
                '件數' => 'E',
                '重量(kg)' => 'F',
                '噸位' => 'G',
                '卡車費' => 'H',
                '堆高機' => 'I',
                '拆板回收' => 'J',
                '備註' => 'K'
            ];
            
            $globalHeaderToDestCol = [];
            foreach ($fixedColumns as $key => $col) {
                $globalHeaderToDestCol[$key] = $col;
            }
            
            $nextExtraColIndex = 12; // L
            foreach ($globalHeaders as $cleanVal) {
                if (!isset($globalHeaderToDestCol[$cleanVal])) {
                    $destColStr = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::stringFromColumnIndex($nextExtraColIndex);
                    $globalHeaderToDestCol[$cleanVal] = $destColStr;
                    $nextExtraColIndex++;
                }
            }

            $feeColumns = []; 
            foreach ($globalHeaderToDestCol as $cleanVal => $destColStr) {
                foreach ($feeKeywords as $keyword) {
                    if (str_contains($cleanVal, $keyword)) {
                        $feeColumns[$destColStr] = [
                            'index' => \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString($destColStr),
                            'total' => 0
                        ];
                        break;
                    }
                }
            }

            // Write first file's header block
            $headerRowCount = count($firstFileHeaderBlock);
            if ($headerRowCount > 0) {
                foreach ($firstFileHeaderBlock as $rIndex => $rowCells) {
                    $isHeaderRow = ($rIndex + 1 === $headerRowCount);
                    
                    if ($isHeaderRow) {
                        $defaultHeaders = [
                            'A' => '日期', 'B' => '客戶名稱', 'C' => '主併提單號碼', 'D' => '送貨地點',
                            'E' => '件數', 'F' => '重量(kg)', 'G' => '噸位', 'H' => '卡車費',
                            'I' => '堆高機', 'J' => '拆板回收', 'K' => '備註'
                        ];
                        foreach ($defaultHeaders as $col => $name) {
                            $activeSheet->getCell($col . $currentRow)->setValue($name);
                            $style = $activeSheet->getStyle($col . $currentRow);
                            $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                        }
                    }
                    
                    foreach ($rowCells as $cleanVal => $value) {
                        if (!isset($globalHeaderToDestCol[$cleanVal])) continue;
                        $destColStr = $globalHeaderToDestCol[$cleanVal];
                        
                        if ($isHeaderRow) {
                            $colIdx = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString($destColStr);
                            if ($colIdx >= 12) {
                                $activeSheet->getCell($destColStr . $currentRow)->setValue($globalHeaderOriginal[$cleanVal] ?? $cleanVal);
                                $style = $activeSheet->getStyle($destColStr . $currentRow);
                                $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                            }
                        } else {
                            $activeSheet->getCell($destColStr . $currentRow)->setValue($value);
                            $style = $activeSheet->getStyle($destColStr . $currentRow);
                            $style->getFont()->setName('微軟正黑體')->setSize(12);
                        }
                    }
                    $currentRow++;
                }
            } else {
                $defaultHeaders = [
                    'A' => '日期', 'B' => '客戶名稱', 'C' => '主併提單號碼', 'D' => '送貨地點',
                    'E' => '件數', 'F' => '重量(kg)', 'G' => '噸位', 'H' => '卡車費',
                    'I' => '堆高機', 'J' => '拆板回收', 'K' => '備註'
                ];
                foreach ($defaultHeaders as $col => $name) {
                    $activeSheet->getCell($col . $currentRow)->setValue($name);
                    $style = $activeSheet->getStyle($col . $currentRow);
                    $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                }
                foreach ($globalHeaders as $cleanVal) {
                    $destColStr = $globalHeaderToDestCol[$cleanVal];
                    $colIdx = \PhpOffice\PhpSpreadsheet\Cell\Coordinate::columnIndexFromString($destColStr);
                    if ($colIdx >= 12) {
                        $activeSheet->getCell($destColStr . $currentRow)->setValue($globalHeaderOriginal[$cleanVal] ?? $cleanVal);
                        $style = $activeSheet->getStyle($destColStr . $currentRow);
                        $style->getFont()->setName('微軟正黑體')->setSize(12)->setBold(true);
                    }
                }
                $currentRow++;
            }

            // --- Output rows ---

            foreach ($allCollectedRows as $rowData) {
                foreach ($rowData['cells'] as $cleanVal => $cellData) {
                    if (!isset($globalHeaderToDestCol[$cleanVal])) continue;
                    $destColStr = $globalHeaderToDestCol[$cleanVal];
                    
                    if ($cellData['is_fee']) {
                        $activeSheet->getCell($destColStr . $currentRow)->setValue($cellData['value']);
                        
                        if (isset($feeColumns[$destColStr])) {
                            $cellValue = $cellData['value'];
                            if (is_numeric($cellValue)) {
                                $feeColumns[$destColStr]['total'] += floatval($cellValue);
                            } else {
                                $val = floatval(str_replace(',', '', (string)$cellValue));
                                $feeColumns[$destColStr]['total'] += $val;
                            }
                        }
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
        $firstFile = reset($files);
        $originalName = $firstFile->getClientOriginalName();
        $filename = pathinfo($originalName, PATHINFO_FILENAME) . '.xlsx';
        $tempDir  = storage_path('app/temp');

        if (!file_exists($tempDir)) {
            mkdir($tempDir, 0755, true);
        }

        $tempPath = $tempDir . '/' . $filename;
        $writer   = new Xlsx($mergedSpreadsheet);
        $writer->save($tempPath);

        // Cleanup temp files if any
        if (!empty($tempFiles)) {
            foreach ($tempFiles as $tempFile) {
                $tempFile = basename($tempFile);
                $filePath = storage_path('app/temp/' . $tempFile);
                if (file_exists($filePath)) {
                    @unlink($filePath);
                }
            }
        }

        return response()->download($tempPath, $filename)->deleteFileAfterSend(true);
    }

    public function uploadTemp(Request $request)
    {
        $request->validate([
            'file' => 'required|file',
        ]);

        $file = $request->file('file');
        $tempName = uniqid('merge_', true) . '_' . preg_replace('/[^a-zA-Z0-9_\-\.]/', '', $file->getClientOriginalName());
        
        $tempDir = storage_path('app/temp');
        if (!file_exists($tempDir)) {
            mkdir($tempDir, 0755, true);
        }

        $file->move($tempDir, $tempName);

        return response()->json([
            'success' => true,
            'temp_name' => $tempName,
            'original_name' => $file->getClientOriginalName()
        ]);
    }
}
