param(
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][string]$QaDirectory
)

$ErrorActionPreference = 'Stop'

function Color([string]$hex) {
  $h=$hex.TrimStart('#')
  $r=[Convert]::ToInt32($h.Substring(0,2),16)
  $g=[Convert]::ToInt32($h.Substring(2,2),16)
  $b=[Convert]::ToInt32($h.Substring(4,2),16)
  return $r + ($g -shl 8) + ($b -shl 16)
}

$C=@{
  Navy=Color '#0D1B2A'; Navy2=Color '#14263B'; Ink=Color '#172033'
  Muted=Color '#667085'; Ivory=Color '#F7F3EA'; Paper=Color '#FFFCF7'
  Rule=Color '#D8D2C7'; Blue=Color '#356CFF'; Mint=Color '#35BFA0'
  Gold=Color '#F2B84B'; Coral=Color '#E76973'; Sky=Color '#DCE7FF'
  MintSoft=Color '#DDF4ED'; GoldSoft=Color '#FCEFD2'; CoralSoft=Color '#F9DFE2'
  White=Color '#FFFFFF'
}

function Add-Text($slide,[string]$value,[double]$left,[double]$top,[double]$width,[double]$height,[double]$size=18,[bool]$bold=$false,[int]$color=$C.Ink,[int]$align=1,[int]$anchor=3) {
  $shape=$slide.Shapes.AddTextbox(1,$left,$top,$width,$height)
  $shape.TextFrame.MarginLeft=2; $shape.TextFrame.MarginRight=2; $shape.TextFrame.MarginTop=1; $shape.TextFrame.MarginBottom=1
  $shape.TextFrame.VerticalAnchor=$anchor
  $shape.TextFrame.WordWrap=-1
  $range=$shape.TextFrame.TextRange
  $range.Text=$value
  $range.Font.Name='Microsoft YaHei'; $range.Font.Size=$size; $range.Font.Bold=if($bold){-1}else{0}; $range.Font.Color.RGB=$color
  $range.ParagraphFormat.Alignment=$align
  return $shape
}

function Add-Rect($slide,[double]$left,[double]$top,[double]$width,[double]$height,[int]$fill=$C.Paper,[int]$line=$C.Rule,[double]$lineWidth=1,[int]$type=1,[double]$transparency=0) {
  $shape=$slide.Shapes.AddShape($type,$left,$top,$width,$height)
  $shape.Fill.ForeColor.RGB=$fill; $shape.Fill.Solid()
  $shape.Fill.Transparency=$transparency
  if($lineWidth -le 0){$shape.Line.Visible=0}else{$shape.Line.Visible=-1;$shape.Line.ForeColor.RGB=$line;$shape.Line.Weight=$lineWidth}
  return $shape
}

function Add-Line($slide,[double]$x1,[double]$y1,[double]$x2,[double]$y2,[int]$color=$C.Rule,[double]$weight=1) {
  $shape=$slide.Shapes.AddLine($x1,$y1,$x2,$y2)
  $shape.Line.ForeColor.RGB=$color; $shape.Line.Weight=$weight
  return $shape
}

function Get-Section([int]$number) {
  if($number -le 4){return @{No='01'; Label='先认识它'; Accent=$C.Blue; Soft=$C.Sky}}
  if($number -le 12){return @{No='02'; Label='第一次准备'; Accent=$C.Mint; Soft=$C.MintSoft}}
  if($number -le 20){return @{No='03'; Label='完成一章'; Accent=$C.Gold; Soft=$C.GoldSoft}}
  if($number -le 30){return @{No='04'; Label='助手与安全'; Accent=$C.Coral; Soft=$C.CoralSoft}}
  return @{No='05'; Label='日常写作'; Accent=$C.Blue; Soft=$C.Sky}
}

function Add-Chrome($slide,[string]$title,[int]$number,[hashtable]$section,[bool]$dark=$false) {
  $base=if($dark){$C.White}else{$C.Ink}
  $muted=if($dark){Color '#AAB7C7'}else{$C.Muted}
  Add-Text $slide ('INKTRACE  /  '+$section.No+'  '+$section.Label) 48 24 540 20 10 $true $muted | Out-Null
  Add-Text $slide $title 48 58 840 62 28 $true $base 1 1 | Out-Null
  Add-Rect $slide 48 128 56 4 $section.Accent $section.Accent 0 | Out-Null
  Add-Text $slide $number.ToString('00') 870 24 42 20 10 $true $muted 3 | Out-Null
}

function Add-Footer($slide,[int]$number,[hashtable]$section,[bool]$dark=$false) {
  $color=if($dark){Color '#AAB7C7'}else{$C.Muted}
  Add-Text $slide ('INKTRACE V2.0  ·  '+$section.Label) 48 510 350 15 9 $false $color | Out-Null
  Add-Line $slide 818 518 866 518 $section.Accent 2 | Out-Null
  Add-Text $slide $number.ToString('00') 875 507 37 18 9 $true $color 3 | Out-Null
}

function Add-Note($slide,[string]$value,[hashtable]$section,[bool]$dark=$false) {
  $fill=if($dark){$C.Navy2}else{$section.Soft}
  $text=if($dark){$C.White}else{$C.Ink}
  Add-Rect $slide 48 438 864 52 $fill $fill 0 5 | Out-Null
  Add-Rect $slide 48 438 7 52 $section.Accent $section.Accent 0 5 | Out-Null
  Add-Text $slide ('记住  '+$value) 70 446 824 34 14 $true $text 1 | Out-Null
}

function Add-Bullets($slide,[string[]]$items,[hashtable]$section) {
  $count=$items.Count
  $cols=if($count -ge 5){2}else{1}
  $rows=[Math]::Ceiling($count/$cols)
  for($i=0;$i -lt $count;$i++){
    $col=if($cols -eq 2){[Math]::Floor($i/$rows)}else{0}
    $row=if($cols -eq 2){$i%$rows}else{$i}
    $left=48+$col*438
    $top=155+$row*82
    $w=if($cols -eq 2){400}else{810}
    Add-Text $slide ($i+1).ToString('00') $left $top 42 31 17 $true $section.Accent | Out-Null
    Add-Line $slide ($left+52) ($top+15) ($left+76) ($top+15) $section.Accent 2 | Out-Null
    Add-Text $slide $items[$i] ($left+88) ($top-2) ($w-88) 48 14.5 $false $C.Ink 1 1 | Out-Null
  }
}

function Add-Column($slide,[string]$heading,[string[]]$items,[double]$left,[double]$width,[int]$number,[int]$accent) {
  Add-Text $slide $number.ToString('00') $left 156 56 44 25 $true $accent | Out-Null
  Add-Text $slide $heading ($left+66) 157 ($width-66) 38 18 $true $C.Ink 1 1 | Out-Null
  Add-Line $slide $left 211 ($left+$width) 211 $accent 2.2 | Out-Null
  $top=if($items.Count -ge 5){220}else{232}
  $gap=if($items.Count -ge 5){40}elseif($items.Count -eq 4){44}else{51}
  $height=if($items.Count -ge 5){31}else{38}
  for($i=0;$i -lt $items.Count;$i++){
    Add-Rect $slide $left ($top+$i*$gap+9) 7 7 $accent $accent 0 9 | Out-Null
    Add-Text $slide $items[$i] ($left+20) ($top+$i*$gap) ($width-20) $height 14.5 $false $C.Ink 1 1 | Out-Null
  }
}

$slides=@(
  @{Kind='cover'; Title="小白写手`n完整操作指南"; Subtitle='从第一次配置，到安全采用每一份候选新稿'; Note='你始终是作者。AI 只准备候选方案，正文、方向、计划和故事记忆都由你确认。'},
  @{Kind='bullets'; Title='先用一句话理解 InkTrace'; Items=@('你负责决定故事；InkTrace 负责整理资料和准备候选方案。','AI 写完以后先进入候选稿区，不会直接修改正式正文。','方向、计划、候选稿和故事记忆，需要分别确认。','预算、分析和风格数据只帮助判断，不替你评价作品。','遇到阻断冲突或费用不明时，系统会先停下等你处理。'); Note='只要记住“先看、再改、再确认”，就不会把 AI 建议误当成正式正文。'},
  @{Kind='columns'; Title='六条安全底线，任何时候都不变'; LeftTitle='不会自动做'; Left=@('不会自动写正式正文','不会自动选择方向或计划','不会自动更新故事记忆'); RightTitle='需要作者做'; Right=@('亲自接受和应用候选稿','处理阻断冲突和预算问题','明确继续、暂停或放弃任务'); Note='关闭写作助手不会删除正文、候选稿或资料。'},
  @{Kind='columns'; Title='先认识四个最常见的词'; LeftTitle='正文与候选'; Left=@('正式正文：你真正保存的小说内容','候选稿：等待你审阅的新稿','候选版本：同一稿件的 v1、v2'); RightTitle='资料与上下文'; Right=@('写作资料：大纲、人物、时间线、伏笔','写作上下文：本次任务的必要资料','故事记忆：保持长篇连续性的正式资料'); Note='候选稿生成成功，只表示“有一份稿可以看”。'},
  @{Kind='steps'; Title='第一次使用，按五步完成准备'; Items=@('创建或导入作品','配置模型并测试连接','打开写作助手','设置预算保护','只生成一章试跑'); Note='第一次不要直接运行很多章。'},
  @{Kind='columns'; Title='新建和导入后，都要先检查作品'; LeftTitle='新建空白作品'; Left=@('在书架选择新建作品','创建第一章','先写一小段并确认保存'); RightTitle='导入已有 TXT'; Right=@('导入前备份并整理章节标题','抽查首章、中间章和末章','检查乱码、漏章和顺序'); Note='拆章有问题时先修复，不要马上初始化。'},
  @{Kind='bullets'; Title='模型配置只需按顺序完成'; Items=@('进入“设置中心 → AI 设置”，添加或选择模型服务。','填写默认模型、服务密钥，以及服务要求的地址。','点击“测试连接”；成功后再配置任务模型。','为分析、规划、写作、审阅和重写任务选择模型。','确认分析和写作任务可用，最后保存 AI 配置。','失败时检查密钥、模型名称、地址、账户权限和网络。'); Note='模型密钥只填在设置页。'},
  @{Kind='columns'; Title='写作助手可以在设置中心直接开关'; LeftTitle='新手先打开'; Left=@('接着写、选区改写','大纲辅助、引用来源','AI 用量与预算、创作分析'); RightTitle='熟悉后再打开'; Right=@('多章续写和自动续写','@引用和风格画像','开篇助手'); Note='开关不会绕过确认，也不会删除历史数据。'},
  @{Kind='columns'; Title='写作台按“章节—正文—辅助”理解'; LeftTitle='左侧和中间'; Left=@('左侧选择和管理章节','中间编辑正式正文','启动 AI 前先确认选对章节'); RightTitle='右侧工作区'; Right=@('管理大纲、人物、时间线和伏笔','使用 AI 助手','集中处理候选稿、冲突和记忆'); Note='切换工具前，如有未保存修改，先保存或明确放弃。'},
  @{Kind='columns'; Title='保存状态决定你下一步该做什么'; LeftTitle='可以继续'; Left=@('已保存：可以切章或关闭','保存中：等待几秒','当前离线：恢复网络后确认'); RightTitle='必须处理'; Right=@('保存失败：按提示重试','版本冲突：选择本地或服务器版本','不确定时先复制重要内容'); Note='不要靠反复刷新解决冲突。'},
  @{Kind='bullets'; Title='已有多章正文时，先做初始化分析'; Items=@('打开作品和有效章节，进入右侧“AI”。','确认使用前检查显示模型配置已完成。','在“初始化分析”点击“启动初始化”。','观察成功、空章节和失败章节数量。','任务可以暂停、继续、取消；失败后可重试。','空章节不是程序故障，失败章节才需要检查。'); Note='初始化不会生成或修改正式正文。'},
  @{Kind='columns'; Title='续写前，先构建当前章节的写作上下文'; LeftTitle='显示可继续'; Left=@('前文和资料已整理','可以进入方向与计划','仍要核对实际意图'); RightTitle='受限或无法继续'; Right=@('补选章节、正文、大纲或人物','确认计划，处理预算或冲突','处理后重新构建'); Note='写作上下文是本次任务的资料包。'},
  @{Kind='steps'; Title='一章候选稿的完整流程'; Items=@('构建上下文','选择方向','确认计划','生成候选稿','审阅并接受','应用到章节草稿'); Note='确认计划不等于接受文字；接受也不等于已经保存正文。'},
  @{Kind='bullets'; Title='选择故事方向时，先看是否适合你的故事'; Items=@('点击“生成方向”，阅读标签和剧情摘要。','优先选择能推进本章主要目标的方向。','检查人物有没有突然改变，秘密有没有提前揭开。','确认它能自然接上上一章，并且一章内能够推进。','由你点击“选择方向”；系统不能替你选择。'); Note='最热闹的方向不一定最好。'},
  @{Kind='columns'; Title='章节计划要说清楚“做什么”和“不做什么”'; LeftTitle='确认前检查'; Left=@('本章主要目标和结尾变化','必须出现的人物、事件或伏笔','暂时禁止发生的事情'); RightTitle='你的操作'; Right=@('满意：确认计划','不满意：拒绝并重新准备','再查看写作任务并确认可执行'); Note='确认计划只允许准备候选稿。'},
  @{Kind='bullets'; Title='生成候选稿前，再看一眼写作任务'; Items=@('查看任务详情，核对目标、必须包含和禁止事项。','任务可执行且内容正确时，点击“确认可执行”。','在“续写与候选稿”点击“生成候选稿”。','等待候选稿出现在列表；正式正文此时不会改变。','执行中可暂停、继续或取消；失败后先看原因。'); Note='候选稿成功 = 有一份稿可以看。'},
  @{Kind='columns'; Title='候选稿至少检查六件事'; LeftTitle='故事连续性'; Left=@('人物：性格、动机、关系和称呼','时间与设定：先后、地点和规则','伏笔：有没有忘记或提前揭晓'); RightTitle='章节质量'; Right=@('情节：目标、因果和结尾','文字：节奏、语气、重复和套话','AI 审阅只能作为第二意见'); Note='最后仍要由你完整通读。'},
  @{Kind='columns'; Title='不满意时，先重写和比较版本'; LeftTitle='重写方式'; Left=@('按 AI 审阅意见修订','输入具体要求后重写','保留事件，只调整对白或节奏'); RightTitle='版本操作'; Right=@('查看 v1、v2 完整内容','查看版本差异','选择真正更合适的版本'); Note='新版本不一定更好。'},
  @{Kind='steps'; Title='接受、应用、保存是三个动作'; Items=@('接受候选稿','应用到章节草稿','作者再次通读和修改','保存正文并看到已保存'); Note='不要在没有通读时连续点击接受和应用。'},
  @{Kind='bullets'; Title='“接着写”适合卡文时快速准备一章'; Items=@('打开正确章节，并确认正文已保存。','进入“AI → AI 助手 → 接着写”。','写一句“本章推进什么 + 暂时不要发生什么”。','选择章节数、目标字数和保护设置后启动。','写完会停下来，等你查看候选稿。','第一次只做一章，不要一次塞入十几个要求。'); Note='示例：接着写旧钥匙线索，但不要揭晓幕后人物。'},
  @{Kind='columns'; Title='多章续写也要逐章看'; LeftTitle='开始前'; Left=@('大纲和人物资料比较完整','接下来几章目标明确','第一次只设置 2—3 章'); RightTitle='运行中'; Right=@('每章结果保留为候选稿','有问题就暂停','取消不删除已生成候选稿'); Note='继续下一章不会采用当前章。'},
  @{Kind='bullets'; Title='自动续写先设置四类保护'; Items=@('填写写作意图、目标章节数和每章字数。','设置本次 AI 用量上限。','选择序列结束、严重冲突和预算超出时停止。','选择伏笔可能提前回收时停止。','先保存保护设置，再启动。','自动续写不自动发书，也不自动更新记忆。'); Note='第一次仍建议只做 2—3 章。'},
  @{Kind='columns'; Title='暂停、停止和放弃，后果完全不同'; LeftTitle='还能恢复'; Left=@('暂停：暂时停下','停止：处理原因后可能恢复','回原任务明确点击继续'); RightTitle='不能恢复'; Right=@('放弃这次：任务永久取消','已有候选稿仍然保留','放弃前会二次确认'); Note='修复预算或资料后也不会自动恢复。'},
  @{Kind='bullets'; Title='大纲辅助的结果先进入草稿'; Items=@('先写清主角目标、阻力和接下来三章。','选择润色、扩写、续写或整理。','对比现在的大纲和建议内容。','检查冲突和建议是否过期。','满意后放进大纲，再回到编辑区检查。','最后手动保存正式大纲。'); Note='大纲变化后，旧建议会过期。'},
  @{Kind='columns'; Title='人物、时间线和伏笔是长篇的基础'; LeftTitle='人物与时间线'; Left=@('人物：姓名、别名、目标、关系和变化','时间线：实际顺序、日期、季节和地点','倒叙和并行线按真实发生时间记录'); RightTitle='伏笔'; Right=@('记录埋下、推进和回收','标明首次出现章节','写清什么时候可以揭晓'); Note='资料变化后及时更新。'},
  @{Kind='columns'; Title='@引用帮助系统找到正确资料'; LeftTitle='怎么使用'; Left=@('在正文输入 @ 和关键词','选择人物、事件或伏笔','鼠标停留查看摘要'); RightTitle='显示异常时'; Right=@('AI 建议引用样式不同','资料变化后可能失效','重新输入 @ 并选择当前资料'); Note='引用不会把内部编号写进最终正文。'},
  @{Kind='bullets'; Title='选区改写只改你选中的那一小段'; Items=@('选中文字，选择扩写、缩写、润色或重写。','扩写补细节；缩写去重复；润色改善表达。','等待新文后，对比原文和新文。','需要时继续手工修改新文。','满意才采用，不满意就拒绝。','应用后重新通读；不合适可以撤销。'); Note='关键场景优先自己写。'},
  @{Kind='columns'; Title='风格画像和开篇助手都只是参考'; LeftTitle='风格画像'; Left=@('选有代表性的自有章节','样本太短时不要过度相信','确认画像只表示允许参考'); RightTitle='开篇助手'; Right=@('先写故事想法，再选开篇方向','参考作品只分析结构','前三章仍然是候选稿'); Note='风格画像不会锁死写法。'},
  @{Kind='columns'; Title='先看引用，再处理冲突'; LeftTitle='引用来源'; Left=@('已确认：来源仍一致','已变化：按当前资料核对','找不到：不要直接相信相关说法'); RightTitle='冲突等级'; Right=@('一般提示：帮助理解','警告：知情后由作者决定','阻断：必须处理后才能应用'); Note='阻断冲突不能被当成警告跳过。'},
  @{Kind='bullets'; Title='应用正文以后，还要单独审阅故事记忆'; Items=@('候选稿可能建议更新人物、设定、事件、时间线或伏笔。','判断内容是否真的发生，而不是计划、猜测或假象。','可以通过、编辑后通过、拒绝或稍后处理。','一组建议确认后，再应用本组修订。','正文采用和记忆更新是两个独立动作。'); Note='只有作者确认后，建议才进入正式故事记忆。'},
  @{Kind='bullets'; Title='预算页面先回答三个问题'; Items=@('本月预计用了多少钱？','本月预算还剩多少？','当前预算状态是否允许继续？','作品可以继承默认预算，也可以单独设置。','手填价格前必须核对服务商官方说明。','费用或用量不明时，系统会保护性停下。'); Note='调高预算后仍要回原功能点击继续。'},
  @{Kind='columns'; Title='创作分析帮你发现现象，不给作品打分'; LeftTitle='可以观察'; Left=@('篇幅、节奏和高潮间隔','对白比例和常用词','风格变化和候选稿使用情况'); RightTitle='正确理解'; Right=@('长篇可能使用缓存','正文变化后可重新统计','AI 使用分析不是 AI 文本检测'); Note='看到异常后，回到章节亲自阅读。'},
  @{Kind='columns'; Title='按钮不见、变灰或任务停住，先找原因'; LeftTitle='入口问题'; Left=@('检查写作助手开关','确认已选章节并完成 AI 配置','检查未保存修改'); RightTitle='任务问题'; Right=@('看是否等待方向、计划或审阅','检查预算、冲突和伏笔保护','处理后回原任务继续'); Note='不要连续创建多个相同任务。'},
  @{Kind='bullets'; Title='每天写一章，按这个顺序最稳'; Items=@('开始前：看上一章结尾、本章目标、人物和伏笔。','写作中：关键场景自己写；卡住时再用接着写。','局部表达不满意时，只改选中的内容。','候选稿完成后，查看全文、引用、审阅和冲突。','满意才接受和应用；然后自己修改并保存。','最后审阅故事记忆，再进入下一章。'); Note='每写完 3—5 章，再更新资料并查看费用和分析。'},
  @{Kind='columns'; Title='封版使用前，完成最后十项检查'; LeftTitle='作品与配置'; Left=@('章节可正常打开和保存','模型连接测试成功','助手可在设置中心开关','预算保护已设置','上下文可以构建'); RightTitle='安全与确认'; Right=@('方向和计划由作者确认','候选稿不会自动进正文','阻断冲突不能跳过','故事记忆单独审批','停止任务不会自动恢复'); Note='全部确认后，再开始较长的多章任务。'},
  @{Kind='closing'; Title="先决定方向`n再准备候选`n看过、改过、确认过`n最后才进入正文"; Note='你始终是作者。'}
)

$ppt=New-Object -ComObject PowerPoint.Application
$presentation=$ppt.Presentations.Add(0)
$presentation.PageSetup.SlideWidth=960; $presentation.PageSetup.SlideHeight=540
try {
  for($i=0;$i -lt $slides.Count;$i++){
    $item=$slides[$i]
    $number=$i+1
    $section=Get-Section $number
    $slide=$presentation.Slides.Add($presentation.Slides.Count+1,12)
    $slide.FollowMasterBackground=0
    $slide.Background.Fill.ForeColor.RGB=$C.Ivory; $slide.Background.Fill.Solid()
    switch($item.Kind){
      'cover' {
        $slide.Background.Fill.ForeColor.RGB=$C.Navy; $slide.Background.Fill.Solid()
        Add-Rect $slide 742 -70 298 298 $C.Blue $C.Blue 0 9 0.15 | Out-Null
        Add-Rect $slide 790 32 180 180 $C.Mint $C.Mint 0 9 0.08 | Out-Null
        Add-Rect $slide 816 70 112 112 $C.Navy $C.Navy 0 9 | Out-Null
        Add-Line $slide 710 88 890 88 $C.Gold 3 | Out-Null
        Add-Text $slide 'INKTRACE  V2.0' 54 44 300 24 11 $true $C.Mint | Out-Null
        Add-Text $slide '给第一次写小说的你' 54 91 420 25 12 $true $(Color '#AAB7C7') | Out-Null
        Add-Text $slide $item.Title 54 136 640 150 48 $true $C.White 1 1 | Out-Null
        Add-Text $slide $item.Subtitle 56 304 700 36 19 $false $(Color '#CBD5E1') | Out-Null
        Add-Line $slide 56 374 174 374 $C.Mint 4 | Out-Null
        Add-Text $slide $item.Note 56 394 760 58 15 $false $C.White 1 1 | Out-Null
        Add-Text $slide '01 / 36' 856 494 56 18 9 $true $(Color '#AAB7C7') 3 | Out-Null
      }
      'bullets' {
        Add-Rect $slide 0 0 18 540 $section.Accent $section.Accent 0 | Out-Null
        Add-Chrome $slide $item.Title $number $section
        Add-Bullets $slide $item.Items $section
        Add-Note $slide $item.Note $section
        Add-Footer $slide $number $section
      }
      'columns' {
        Add-Rect $slide 0 0 18 540 $section.Accent $section.Accent 0 | Out-Null
        Add-Chrome $slide $item.Title $number $section
        Add-Column $slide $item.LeftTitle $item.Left 48 400 1 $section.Accent
        Add-Line $slide 472 156 472 397 $C.Rule 1.2 | Out-Null
        Add-Column $slide $item.RightTitle $item.Right 500 412 2 $(if($section.Accent -eq $C.Coral){$C.Gold}else{$C.Mint})
        Add-Note $slide $item.Note $section
        Add-Footer $slide $number $section
      }
      'steps' {
        $slide.Background.Fill.ForeColor.RGB=$C.Navy; $slide.Background.Fill.Solid()
        Add-Chrome $slide $item.Title $number $section $true
        $count=$item.Items.Count; $gap=22; $width=(836-$gap*($count-1))/$count
        Add-Line $slide 90 252 870 252 $(Color '#526477') 2 | Out-Null
        for($j=0;$j -lt $count;$j++){
          $left=62+$j*($width+$gap)
          $circleLeft=$left+($width-48)/2
          $fill=if($j -eq $count-1){$section.Accent}else{$C.Navy2}
          Add-Rect $slide $circleLeft 228 48 48 $fill $fill 0 9 | Out-Null
          Add-Text $slide ($j+1).ToString('00') $circleLeft 234 48 34 15 $true $C.White 2 | Out-Null
          $textTop=if($j%2 -eq 0){162}else{298}
          Add-Line $slide ($circleLeft+24) $(if($j%2 -eq 0){214}else{276}) ($circleLeft+24) $(if($j%2 -eq 0){228}else{298}) $section.Accent 2 | Out-Null
          Add-Text $slide $item.Items[$j] $left $textTop $width 54 14.5 $true $C.White 2 1 | Out-Null
        }
        Add-Note $slide $item.Note $section $true
        Add-Footer $slide $number $section $true
      }
      'closing' {
        $slide.Background.Fill.ForeColor.RGB=$C.Navy; $slide.Background.Fill.Solid()
        Add-Rect $slide -65 355 255 255 $C.Blue $C.Blue 0 9 0.18 | Out-Null
        Add-Rect $slide 805 -40 185 185 $C.Mint $C.Mint 0 9 0.12 | Out-Null
        Add-Text $slide 'INKTRACE  /  写作的决定权始终在你手里' 54 43 600 24 11 $true $C.Mint | Out-Null
        Add-Text $slide $item.Title 110 105 740 250 34 $true $C.White 2 1 | Out-Null
        Add-Line $slide 350 382 610 382 $C.Gold 4 | Out-Null
        Add-Text $slide $item.Note 150 410 660 44 20 $true $C.Mint 2 | Out-Null
        Add-Text $slide '36 / 36' 854 494 58 18 9 $true $(Color '#AAB7C7') 3 | Out-Null
      }
    }
  }
  New-Item -ItemType Directory -Path $QaDirectory -Force | Out-Null
  $resolvedOutput=[System.IO.Path]::GetFullPath($OutputPath)
  $presentation.SaveAs($resolvedOutput,24)
  for($i=1;$i -le $presentation.Slides.Count;$i++){
    $png=Join-Path $QaDirectory ('slide-{0:D2}.png' -f $i)
    $presentation.Slides.Item($i).Export($png,'PNG',1600,900)
  }
  Write-Output $resolvedOutput
} finally {
  $presentation.Close()
  $ppt.Quit()
}
