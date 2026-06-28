<?php
$row = [
    'A' => '',
    'B' => '',
    'C' => '',
    'D' => '',
    'E' => '',
    'F' => '',
    'G' => '0',
    'H' => '18300',
    'I' => ''
];
$feeColumns = [
    'H' => ['index' => 8, 'srcCol' => 'G', 'name' => '卡車費'],
    'I' => ['index' => 9, 'srcCol' => 'H', 'name' => '代墊款']
];
$dateColString = 'A';
$hasData = false;
$isTotalRow = false;
$hasFeeData = false;
$hasNonZeroNonFeeData = false;

foreach ($row as $colStr => $cellVal) {
    if ($colStr !== $dateColString && $cellVal !== '') {
        $hasData = true;
    }
    
    if (str_contains($cellVal, '總計') || str_contains($cellVal, '合計') || str_contains($cellVal, '總額') || str_contains($cellVal, '總金額') || str_contains($cellVal, '小計')) {
        $isTotalRow = true;
    }
    
    if (isset($feeColumns[$colStr]) && $cellVal !== '') {
        $cleanVal = str_replace(',', '', $cellVal);
        if (is_numeric($cleanVal)) {
            $hasFeeData = true;
        }
    } elseif ($cellVal !== '' && $cellVal !== '0' && $cellVal !== '0.0' && $cellVal !== '0.00' && $cellVal !== '0.000' && $cellVal !== '-') {
        $hasNonZeroNonFeeData = true;
        echo "Non-zero non-fee data found at $colStr: '$cellVal'\n";
    }
}
echo "hasFeeData: " . ($hasFeeData ? 'true' : 'false') . "\n";
echo "hasNonZeroNonFeeData: " . ($hasNonZeroNonFeeData ? 'true' : 'false') . "\n";
if ($hasFeeData && !$hasNonZeroNonFeeData) {
    $isTotalRow = true;
}
echo "isTotalRow: " . ($isTotalRow ? 'true' : 'false') . "\n";
