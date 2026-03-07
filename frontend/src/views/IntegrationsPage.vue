<template>
  <div class="px-4 py-5 md:p-6">
    <div class="mx-auto max-w-[1200px]">
      <div class="mb-6 flex flex-col gap-2 sm:gap-3">
        <h1 class="text-2xl font-semibold">插件与联动</h1>
        <p class="text-sm text-muted-foreground">管理 AI API、TTS、HFish、Nmap、推送通道与防火墙联动配置</p>
      </div>

      <Tabs default-value="hfish" class="space-y-6">
        <TabsList class="mb-6 h-auto w-full justify-start gap-1 overflow-x-auto rounded-2xl p-1.5 sm:flex-wrap sm:overflow-visible">
          <TabsTrigger value="hfish" class="flex shrink-0 items-center gap-1.5 px-4 py-2">
            <Bug class="size-3.5" />
            HFish 蜜罐
          </TabsTrigger>
          <TabsTrigger value="nmap" class="flex shrink-0 items-center gap-1.5 px-4 py-2">
            <Zap class="size-3.5" />
            Nmap 扫描
          </TabsTrigger>
          <TabsTrigger value="push" class="flex shrink-0 items-center gap-1.5 px-4 py-2">
            <BellRing class="size-3.5" />
            推送通道
          </TabsTrigger>
          <TabsTrigger value="device" class="flex shrink-0 items-center gap-1.5 px-4 py-2">
            <Server class="size-3.5" />
            设备凭证
          </TabsTrigger>
          <TabsTrigger value="ai" class="flex shrink-0 items-center gap-1.5 px-4 py-2">
            <BrainCircuit class="size-3.5" />
            AI / TTS
          </TabsTrigger>
          <TabsTrigger value="firewall" class="flex shrink-0 items-center gap-1.5 px-4 py-2">
            <Shield class="size-3.5" />
            防火墙联动
          </TabsTrigger>
        </TabsList>

        <!-- ── HFish 蜜罐 ── -->
        <TabsContent value="hfish">
          <Card>
            <CardHeader class="flex-col gap-3 pb-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="space-y-0.5">
                <CardTitle class="text-base flex items-center gap-2">
                  <Bug class="size-4 text-amber-400" />
                  HFish 蜜罐接入
                </CardTitle>
                <p class="text-xs text-muted-foreground">配置 HFish API 连接，启用蜜罐攻击日志自动同步</p>
              </div>
              <Badge :class="hfishConfig.enabled ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-muted text-muted-foreground'">
                {{ hfishConfig.enabled ? '已启用' : '未启用' }}
              </Badge>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-1.5">
                  <label class="text-sm font-medium">HFish 地址（host:port）</label>
                  <input
                    v-model="hfishForm.host_port"
                    type="text"
                    placeholder="127.0.0.1:4433"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium">API 密钥</label>
                  <input
                    v-model="hfishForm.api_key"
                    type="password"
                    placeholder="留空则不修改当前密钥"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5 md:col-span-2">
                  <label class="text-sm font-medium">蜜罐 API 接口地址（完整 URL）</label>
                  <input
                    v-model="hfishForm.api_base_url"
                    type="text"
                    placeholder="https://192.168.1.100:4433（留空则自动拼接 host:port）"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                  />
                  <p class="text-xs text-muted-foreground">自定义蜜罐系统的完整基础 URL，支持 HTTP/HTTPS 和自定义路径前缀；留空则默认使用 https://host:port</p>
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium">同步间隔（秒）</label>
                  <input
                    v-model.number="hfishForm.sync_interval"
                    type="number"
                    min="10"
                    max="86400"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <p class="text-xs text-muted-foreground">最小 10 秒，建议 60 秒</p>
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium">启用状态</label>
                  <div class="flex items-center gap-3 pt-1.5">
                    <button
                      type="button"
                      role="switch"
                      :aria-checked="hfishForm.enabled ? 'true' : 'false'"
                      :aria-label="hfishForm.enabled ? 'Disable HFish sync' : 'Enable HFish sync'"
                      :class="[
                        'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                        hfishForm.enabled ? 'bg-primary' : 'bg-input',
                      ]"
                      @click="hfishForm.enabled = !hfishForm.enabled"
                    >
                      <span
                        :class="[
                          'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                          hfishForm.enabled ? 'translate-x-4' : 'translate-x-0',
                        ]"
                      />
                    </button>
                    <span class="text-sm text-muted-foreground">{{ hfishForm.enabled ? '自动同步已开启' : '自动同步已关闭' }}</span>
                  </div>
                </div>
              </div>
              <div class="flex flex-col items-start gap-2 border-t border-border pt-2 sm:flex-row sm:flex-wrap sm:items-center">
                <Button size="sm" class="cursor-pointer" :disabled="hfishSaving" @click="saveHFishConfig">
                  <span v-if="hfishSaving">保存中…</span>
                  <span v-else>保存配置</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="cursor-pointer gap-1.5"
                  :disabled="!hfishConfig.enabled || hfishSyncing"
                  @click="triggerHFishSync"
                >
                  <RefreshCw class="size-3.5" :class="hfishSyncing ? 'animate-spin' : ''" />
                  立即同步
                </Button>
                <span v-if="hfishMsg" :class="hfishMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs ml-1">
                  {{ hfishMsg }}
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <!-- ── Nmap 扫描 ── -->
        <TabsContent value="nmap">
          <Card>
            <CardHeader class="flex-col gap-3 pb-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="space-y-0.5">
                <CardTitle class="text-base flex items-center gap-2">
                  <Zap class="size-4 text-blue-400" />
                  Nmap 网络扫描
                </CardTitle>
                <p class="text-xs text-muted-foreground">配置 Nmap 可执行路径与扫描目标，启用定时探测</p>
              </div>
              <Badge :class="nmapConfig.enabled ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-muted text-muted-foreground'">
                {{ nmapConfig.enabled ? '已启用' : '未启用' }}
              </Badge>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-1.5 md:col-span-2">
                  <label class="text-sm font-medium">Nmap 可执行路径</label>
                  <input
                    v-model="nmapForm.nmap_path"
                    type="text"
                    placeholder="C:\nmap\nmap.exe 或 /usr/bin/nmap"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5 md:col-span-2">
                  <label class="text-sm font-medium">扫描 IP 范围（每行一个）</label>
                  <textarea
                    v-model="nmapIpRangesText"
                    rows="3"
                    placeholder="192.168.1.0/24&#10;10.0.0.1-255&#10;172.16.0.100"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none font-mono"
                  />
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium">扫描间隔（秒）</label>
                  <input
                    v-model.number="nmapForm.scan_interval"
                    type="number"
                    min="60"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <p class="text-xs text-muted-foreground">默认 604800（7天）</p>
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium">启用状态</label>
                  <div class="flex items-center gap-3 pt-1.5">
                    <button
                      type="button"
                      role="switch"
                      :aria-checked="nmapForm.enabled ? 'true' : 'false'"
                      :aria-label="nmapForm.enabled ? 'Disable scheduled Nmap scan' : 'Enable scheduled Nmap scan'"
                      :class="[
                        'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                        nmapForm.enabled ? 'bg-primary' : 'bg-input',
                      ]"
                      @click="nmapForm.enabled = !nmapForm.enabled"
                    >
                      <span
                        :class="[
                          'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                          nmapForm.enabled ? 'translate-x-4' : 'translate-x-0',
                        ]"
                      />
                    </button>
                    <span class="text-sm text-muted-foreground">{{ nmapForm.enabled ? '定时扫描已开启' : '定时扫描已关闭' }}</span>
                  </div>
                </div>
              </div>

              <div class="flex flex-col items-start gap-2 border-t border-border pt-2 sm:flex-row sm:flex-wrap sm:items-center">
                <Button size="sm" class="cursor-pointer" :disabled="nmapSaving" @click="saveNmapConfig">
                  <span v-if="nmapSaving">保存中…</span>
                  <span v-else>保存配置</span>
                </Button>
                <span v-if="nmapMsg" :class="nmapMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs ml-1">
                  {{ nmapMsg }}
                </span>
              </div>

              <!-- 漏洞检测规则 -->
              <div class="pt-3 border-t border-border space-y-3">
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div class="space-y-0.5">
                    <p class="text-sm font-medium flex items-center gap-1.5">
                      <Bug class="size-3.5 text-red-400" />
                      漏洞检测脚本规则
                    </p>
                    <p class="text-xs text-muted-foreground">按系统标签配置 Nmap 漏洞检测脚本，系统自动识别主机 OS 后执行对应脚本</p>
                  </div>
                  <Button variant="outline" size="sm" class="cursor-pointer gap-1" @click="addVulnTag">
                    <Plus class="size-3.5" />
                    添加标签
                  </Button>
                </div>

                <div class="space-y-2">
                  <div
                    v-for="(scripts, tag) in vulnScriptsMap"
                    :key="tag"
                    class="rounded-lg border border-border p-3 space-y-2 bg-muted/10"
                  >
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div class="flex items-center gap-2">
                        <Badge variant="outline" class="text-xs font-mono">{{ tag }}</Badge>
                        <span class="text-xs text-muted-foreground">{{ scripts.length }} 个脚本</span>
                      </div>
                      <button
                        type="button"
                        :aria-label="'Remove tag ' + tag"
                        class="text-xs text-destructive/70 hover:text-destructive cursor-pointer"
                        @click="removeVulnTag(tag)"
                      >删除标签</button>
                    </div>
                    <div class="flex flex-wrap gap-1.5">
                      <div
                        v-for="(script, idx) in scripts"
                        :key="idx"
                        class="flex items-center gap-1 bg-muted/50 rounded px-2 py-0.5 text-xs font-mono"
                      >
                        <span>{{ script }}</span>
                        <button
                          type="button"
                          :aria-label="'Remove script ' + script"
                          class="text-muted-foreground hover:text-destructive cursor-pointer ml-1"
                          @click="removeScript(tag, idx)"
                        >×</button>
                      </div>
                      <button
                        type="button"
                        class="flex items-center gap-0.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer border border-dashed border-border rounded px-2 py-0.5"
                        @click="addScript(tag)"
                      >
                        <Plus class="size-3" /> 添加脚本
                      </button>
                    </div>
                  </div>
                  <div v-if="Object.keys(vulnScriptsMap).length === 0" class="text-center py-4 text-xs text-muted-foreground border border-dashed border-border rounded-lg">
                    暂无规则，点击「添加标签」开始配置
                  </div>
                </div>

                <div class="flex flex-col items-start gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <Button size="sm" variant="outline" class="cursor-pointer" :disabled="nmapSaving" @click="saveVulnScripts">
                    保存漏洞规则
                  </Button>
                  <span v-if="vulnMsg" :class="vulnMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs">{{ vulnMsg }}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <!-- ── 推送通道 ── -->
        <TabsContent value="push">
          <Card>
            <CardHeader class="flex-col gap-3 pb-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="space-y-0.5">
                <CardTitle class="text-base flex items-center gap-2">
                  <BellRing class="size-4 text-purple-400" />
                  推送通道
                </CardTitle>
                <p class="text-xs text-muted-foreground">管理 Webhook / 企微 / 钉钉 / 邮件通知通道</p>
              </div>
              <Button variant="outline" size="sm" class="cursor-pointer gap-1.5" @click="showAddChannel = !showAddChannel">
                <Plus class="size-3.5" />
                新建通道
              </Button>
            </CardHeader>
            <CardContent class="space-y-4">
              <div v-if="showAddChannel" class="rounded-lg border border-border p-4 space-y-3 bg-muted/20">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">通道类型</label>
                    <select
                      v-model="channelForm.channel_type"
                      class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    >
                      <option value="webhook">Webhook</option>
                      <option value="wecom">企业微信</option>
                      <option value="dingtalk">钉钉</option>
                      <option value="email">邮件</option>
                    </select>
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">通道名称</label>
                    <input
                      v-model="channelForm.channel_name"
                      placeholder="例如：运维告警群"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-sm font-medium">目标地址（Webhook URL / 邮箱）</label>
                    <input
                      v-model="channelForm.target"
                      placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                    />
                  </div>
                </div>
                <div class="flex flex-col items-start gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <Button size="sm" class="cursor-pointer" :disabled="channelCreating" @click="createChannel">
                    {{ channelCreating ? '创建中…' : '创建' }}
                  </Button>
                  <Button variant="ghost" size="sm" class="cursor-pointer" @click="showAddChannel = false">取消</Button>
                  <span v-if="channelMsg" class="text-xs" :class="channelMsgOk ? 'text-emerald-400' : 'text-destructive'">{{ channelMsg }}</span>
                </div>
              </div>

              <div v-if="channelsLoading" class="space-y-2">
                <Skeleton v-for="i in 2" :key="i" class="h-14 w-full rounded" />
              </div>
              <div v-else-if="safeChannels.length === 0" class="py-6 text-center text-sm text-muted-foreground">
                暂无推送通道
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="ch in safeChannels"
                  :key="ch.id"
                  class="flex flex-col gap-3 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div class="space-y-0.5 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-sm">{{ ch.channel_name }}</span>
                      <Badge variant="outline" class="text-[10px] h-4 capitalize">{{ ch.channel_type }}</Badge>
                      <Badge
                        :class="ch.enabled ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-muted text-muted-foreground'"
                        class="text-[10px] h-4"
                      >{{ ch.enabled ? '启用' : '禁用' }}</Badge>
                    </div>
                    <p class="text-xs text-muted-foreground truncate max-w-[360px] font-mono">{{ ch.target }}</p>
                  </div>
                  <div class="flex items-center gap-1.5 shrink-0">
                    <Button variant="outline" size="sm" class="cursor-pointer text-xs h-7 gap-1" @click="toggleChannel(ch)">
                      {{ ch.enabled ? '禁用' : '启用' }}
                    </Button>
                    <Button variant="outline" size="sm" class="cursor-pointer text-xs h-7 gap-1" @click="testChannel(ch.id)">
                      测试
                    </Button>
                    <Button variant="ghost" size="sm" class="cursor-pointer text-destructive text-xs h-7" @click="deleteChannel(ch.id)">
                      删除
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <!-- ── 设备凭证 ── -->
        <TabsContent value="device">
          <Card>
            <CardHeader class="flex-col gap-3 pb-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="space-y-0.5">
                <CardTitle class="text-base flex items-center gap-2">
                  <Server class="size-4 text-cyan-400" />
                  交换机 / 设备凭证管理
                </CardTitle>
                <p class="text-xs text-muted-foreground">管理网络设备的 SSH/Telnet 登录凭证，支持每台设备多组密码</p>
              </div>
              <Button variant="outline" size="sm" class="cursor-pointer gap-1.5" @click="showAddDevice = !showAddDevice">
                <Plus class="size-3.5" />
                添加设备
              </Button>
            </CardHeader>
            <CardContent class="space-y-4">
              <div v-if="showAddDevice" class="rounded-lg border border-border p-4 space-y-3 bg-muted/20">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">设备名称</label>
                    <input v-model="deviceForm.name" placeholder="如：核心交换机-1"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">IP 地址</label>
                    <input v-model="deviceForm.ip" placeholder="192.168.1.1"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">端口</label>
                    <input v-model.number="deviceForm.port" type="number" min="1" max="65535"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">厂商</label>
                    <select v-model="deviceForm.vendor"
                      class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring">
                      <option value="huawei">华为</option>
                      <option value="h3c">H3C</option>
                      <option value="cisco">Cisco</option>
                      <option value="ruijie">锐捷</option>
                      <option value="other">其他</option>
                    </select>
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">设备类型</label>
                    <input v-model="deviceForm.device_type" placeholder="交换机 / 路由器 / 防火墙"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring" />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium">备注</label>
                    <input v-model="deviceForm.description" placeholder="可选"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring" />
                  </div>
                </div>
                <div class="flex flex-col items-start gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <Button size="sm" class="cursor-pointer" :disabled="deviceCreating" @click="createDevice">
                    {{ deviceCreating ? '创建中…' : '创建设备' }}
                  </Button>
                  <Button variant="ghost" size="sm" class="cursor-pointer" @click="showAddDevice = false">取消</Button>
                  <span v-if="deviceMsg" class="text-xs" :class="deviceMsgOk ? 'text-emerald-400' : 'text-destructive'">{{ deviceMsg }}</span>
                </div>
              </div>

              <div v-if="devicesLoading" class="space-y-2">
                <Skeleton v-for="i in 2" :key="i" class="h-20 w-full rounded" />
              </div>
              <div v-else-if="safeDevices.length === 0" class="py-6 text-center text-sm text-muted-foreground">
                暂无已配置设备
              </div>
              <div v-else class="space-y-3">
                <div v-for="dev in safeDevices" :key="dev.id" class="rounded-lg border border-border p-4 space-y-3">
                  <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div class="space-y-0.5">
                      <div class="flex items-center gap-2">
                        <span class="font-medium text-sm">{{ dev.name }}</span>
                        <Badge variant="outline" class="text-[10px] h-4 capitalize">{{ dev.vendor }}</Badge>
                        <Badge v-if="dev.device_type" variant="outline" class="text-[10px] h-4">{{ dev.device_type }}</Badge>
                        <Badge :class="dev.enabled ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-muted text-muted-foreground'" class="text-[10px] h-4">
                          {{ dev.enabled ? '启用' : '禁用' }}
                        </Badge>
                      </div>
                      <p class="text-xs text-muted-foreground font-mono">{{ dev.ip }}:{{ dev.port }}</p>
                    </div>
                    <div class="flex items-center gap-1.5 shrink-0">
                      <Button variant="outline" size="sm" class="cursor-pointer text-xs h-7" @click="toggleDevice(dev)">
                        {{ dev.enabled ? '禁用' : '启用' }}
                      </Button>
                      <Button variant="ghost" size="sm" class="cursor-pointer text-destructive text-xs h-7" @click="removeDevice(dev.id)">
                        删除
                      </Button>
                    </div>
                  </div>

                  <div class="space-y-1.5">
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <span class="text-xs font-medium text-muted-foreground">登录凭证（{{ dev.credentials?.length || 0 }}）</span>
                      <button type="button" class="text-xs text-primary hover:underline cursor-pointer" @click="promptAddCredential(dev.id)">
                        + 添加凭证
                      </button>
                    </div>
                    <div v-if="dev.credentials && dev.credentials.length > 0" class="space-y-1">
                      <div v-for="cred in dev.credentials" :key="cred.id"
                        class="flex flex-col gap-2 rounded border border-border/50 bg-muted/10 px-3 py-1.5 sm:flex-row sm:items-center sm:justify-between">
                        <div class="flex items-center gap-3 text-xs">
                          <span class="font-mono">{{ cred.username }}</span>
                          <span class="text-muted-foreground">********</span>
                        </div>
                        <div class="flex items-center gap-1">
                          <button type="button" class="text-xs text-primary hover:underline cursor-pointer" @click="promptUpdateCredential(dev.id, cred)">
                            修改
                          </button>
                          <button type="button" class="text-xs text-destructive/70 hover:text-destructive cursor-pointer ml-2" @click="removeCredential(dev.id, cred.id)">
                            删除
                          </button>
                        </div>
                      </div>
                    </div>
                    <div v-else class="text-xs text-muted-foreground/60 py-1">暂无凭证，请添加</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <!-- ── AI / TTS ── -->
        <TabsContent value="ai">
          <div class="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader class="pb-2">
                <CardTitle class="text-sm flex items-center gap-2">
                  <BrainCircuit class="size-4 text-muted-foreground" />
                  AI API 配置
                </CardTitle>
              </CardHeader>
              <CardContent class="space-y-3">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="space-y-1.5">
                    <label class="text-xs font-medium text-muted-foreground">Provider</label>
                    <input
                      v-model="aiApiForm.provider"
                      type="text"
                      placeholder="ollama / localai / openai"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-xs font-medium text-muted-foreground">模型名称</label>
                    <input
                      v-model="aiApiForm.model_name"
                      type="text"
                      placeholder="llama2 / qwen2.5 / gpt-4.1"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-xs font-medium text-muted-foreground">API 基础地址</label>
                    <input
                      v-model="aiApiForm.base_url"
                      type="text"
                      placeholder="http://localhost:11434"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-xs font-medium text-muted-foreground">API Key（留空不修改）</label>
                    <input
                      v-model="aiApiForm.api_key"
                      type="password"
                      placeholder="可选，适用于云模型"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-xs font-medium text-muted-foreground">启用状态</label>
                    <div class="flex items-center gap-3 pt-1">
                      <button
                        type="button"
                        role="switch"
                        :aria-checked="aiApiForm.enabled ? 'true' : 'false'"
                        :aria-label="aiApiForm.enabled ? 'Disable AI API' : 'Enable AI API'"
                        :class="[
                          'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                          aiApiForm.enabled ? 'bg-primary' : 'bg-input',
                        ]"
                        @click="aiApiForm.enabled = !aiApiForm.enabled"
                      >
                        <span
                          :class="[
                            'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                            aiApiForm.enabled ? 'translate-x-4' : 'translate-x-0',
                          ]"
                        />
                      </button>
                      <span class="text-xs text-muted-foreground">{{ aiApiForm.enabled ? 'AI API 已启用' : 'AI API 已禁用' }}</span>
                      <Badge
                        v-if="aiApiConfig?.api_key_configured"
                        class="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px]"
                      >
                        已配置 API Key
                      </Badge>
                    </div>
                  </div>
                </div>
                <div class="flex flex-col items-start gap-2 border-t border-border pt-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <Button size="sm" class="cursor-pointer" :disabled="aiApiSaving" @click="saveAIApiConfig">
                    <span v-if="aiApiSaving">保存中…</span>
                    <span v-else>保存 AI 配置</span>
                  </Button>
                  <span v-if="aiApiMsg" :class="aiApiMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs">
                    {{ aiApiMsg }}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader class="pb-2">
                <CardTitle class="text-sm flex items-center gap-2">
                  <Volume2 class="size-4 text-muted-foreground" />
                  TTS 语音配置
                </CardTitle>
              </CardHeader>
              <CardContent class="space-y-3">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="space-y-1.5">
                    <label class="text-xs font-medium text-muted-foreground">Provider</label>
                    <input
                      v-model="ttsEngineForm.provider"
                      type="text"
                      placeholder="local / coqui / piper / cloud"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-xs font-medium text-muted-foreground">模型名称</label>
                    <input
                      v-model="ttsEngineForm.model_name"
                      type="text"
                      placeholder="local-tts-v1"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-xs font-medium text-muted-foreground">服务地址（可选）</label>
                    <input
                      v-model="ttsEngineForm.endpoint"
                      type="text"
                      placeholder="http://localhost:5002"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-xs font-medium text-muted-foreground">语音模型/音色</label>
                    <input
                      v-model="ttsEngineForm.voice_model"
                      type="text"
                      placeholder="zh-CN-female-1"
                      class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5 sm:col-span-2">
                    <label class="text-xs font-medium text-muted-foreground">启用状态</label>
                    <div class="flex items-center gap-3 pt-1">
                      <button
                        type="button"
                        role="switch"
                        :aria-checked="ttsEngineForm.enabled ? 'true' : 'false'"
                        :aria-label="ttsEngineForm.enabled ? 'Disable TTS' : 'Enable TTS'"
                        :class="[
                          'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                          ttsEngineForm.enabled ? 'bg-primary' : 'bg-input',
                        ]"
                        @click="ttsEngineForm.enabled = !ttsEngineForm.enabled"
                      >
                        <span
                          :class="[
                            'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                            ttsEngineForm.enabled ? 'translate-x-4' : 'translate-x-0',
                          ]"
                        />
                      </button>
                      <span class="text-xs text-muted-foreground">{{ ttsEngineForm.enabled ? 'TTS 已启用' : 'TTS 已禁用' }}</span>
                      <Badge class="bg-muted text-muted-foreground text-[10px]">
                        当前模型: {{ ttsEngineConfig?.model_name || 'local-tts-v1' }}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div class="flex flex-col items-start gap-2 border-t border-border pt-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <Button size="sm" class="cursor-pointer" :disabled="ttsEngineSaving" @click="saveTTSConfig">
                    <span v-if="ttsEngineSaving">保存中…</span>
                    <span v-else>保存 TTS 配置</span>
                  </Button>
                  <span v-if="ttsEngineMsg" :class="ttsEngineMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs">
                    {{ ttsEngineMsg }}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card class="opacity-70 md:col-span-2">
              <CardHeader class="pb-2">
                <CardTitle class="text-sm flex items-center gap-2">
                  <Shield class="size-4 text-muted-foreground" />
                  MCP 执行器
                </CardTitle>
              </CardHeader>
              <CardContent class="text-xs text-muted-foreground space-y-1">
                <p>交换机封禁与回滚工具调用链路（stdio/sse 通信）</p>
                <Badge class="bg-muted text-muted-foreground text-xs">已集成</Badge>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <!-- ── 防火墙联动 ── -->
        <TabsContent value="firewall">
          <Card>
            <CardHeader class="pb-2">
              <CardTitle class="text-sm flex items-center gap-2">
                <Zap class="size-4 text-muted-foreground" />
                防火墙同步
              </CardTitle>
            </CardHeader>
            <CardContent class="space-y-3">
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5 sm:col-span-2">
                  <label class="text-xs font-medium text-muted-foreground">防火墙 API 基础地址</label>
                  <input
                    v-model="firewallForm.api_base_url"
                    type="text"
                    placeholder="https://firewall.example.com/api"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                  />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-medium text-muted-foreground">默认厂商</label>
                  <input
                    v-model="firewallForm.default_vendor"
                    type="text"
                    placeholder="generic / huawei / h3c / fortigate"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-medium text-muted-foreground">默认策略 ID</label>
                  <input
                    v-model="firewallForm.default_policy_id"
                    type="text"
                    placeholder="可选"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-medium text-muted-foreground">请求超时（秒）</label>
                  <input
                    v-model.number="firewallForm.timeout_seconds"
                    type="number"
                    min="1"
                    max="300"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-medium text-muted-foreground">签名密钥（留空不修改）</label>
                  <input
                    v-model="firewallForm.sign_secret"
                    type="password"
                    placeholder="新的 HMAC 密钥"
                    class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <label class="text-xs font-medium text-muted-foreground">启用状态</label>
                  <div class="flex items-center gap-3 pt-1">
                    <button
                      type="button"
                      role="switch"
                      :aria-checked="firewallForm.enabled ? 'true' : 'false'"
                      :aria-label="firewallForm.enabled ? 'Disable firewall sync' : 'Enable firewall sync'"
                      :class="[
                        'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                        firewallForm.enabled ? 'bg-primary' : 'bg-input',
                      ]"
                      @click="firewallForm.enabled = !firewallForm.enabled"
                    >
                      <span
                        :class="[
                          'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                          firewallForm.enabled ? 'translate-x-4' : 'translate-x-0',
                        ]"
                      />
                    </button>
                    <span class="text-xs text-muted-foreground">{{ firewallForm.enabled ? '防火墙联动已启用' : '防火墙联动已禁用' }}</span>
                    <Badge
                      v-if="firewallConfig.has_custom_sign_secret"
                      class="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px]"
                    >
                      已配置自定义签名密钥
                    </Badge>
                  </div>
                </div>
              </div>
              <div class="flex flex-col items-start gap-2 border-t border-border pt-2 sm:flex-row sm:flex-wrap sm:items-center">
                <Button size="sm" class="cursor-pointer" :disabled="firewallSaving" @click="saveFirewallConfig">
                  <span v-if="firewallSaving">保存中…</span>
                  <span v-else>保存防火墙配置</span>
                </Button>
                <span v-if="firewallMsg" :class="firewallMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs">
                  {{ firewallMsg }}
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog :open="promptDialog.open" @update:open="handlePromptDialogToggle">
        <DialogContent class="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>{{ promptDialog.title }}</DialogTitle>
            <DialogDescription>{{ promptDialog.description }}</DialogDescription>
          </DialogHeader>
          <div class="space-y-3 pt-2">
            <div v-for="field in promptDialog.fields" :key="field.key" class="space-y-1.5">
              <label class="text-sm font-medium">{{ field.label }}</label>
              <input
                v-model="field.value"
                :type="field.type"
                :placeholder="field.placeholder"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" class="cursor-pointer" @click="closePromptDialog(null)">取消</Button>
            <Button class="cursor-pointer" @click="submitPromptDialog">{{ promptDialog.confirmLabel }}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog :open="confirmDialog.open" @update:open="handleConfirmDialogToggle">
        <DialogContent class="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>{{ confirmDialog.title }}</DialogTitle>
            <DialogDescription>{{ confirmDialog.description }}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" class="cursor-pointer" @click="closeConfirmDialog(false)">取消</Button>
            <Button class="cursor-pointer" @click="closeConfirmDialog(true)">{{ confirmDialog.confirmLabel }}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { BellRing, BrainCircuit, Bug, Plus, RefreshCw, Server, Shield, Volume2, Zap } from 'lucide-vue-next'
import { apiClient, getRequestErrorMessage, hasAccessToken } from '@/api/client'
import { defenseApi, type HFishConfig } from '@/api/defense'
import { scanApi } from '@/api/scan'
import { deviceApi, type DeviceInfo, type DeviceCredential } from '@/api/device'
import { firewallApi, type FirewallConfig } from '@/api/firewall'
import { systemApi, type AIAPIConfig, type TTSConfig } from '@/api/system'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'

// ── HFish 状态 ──
const hfishConfig = ref<HFishConfig>({ host_port: null, api_base_url: null, sync_interval: 60, enabled: false })
const hfishForm = reactive({ host_port: '', api_base_url: '', api_key: '', sync_interval: 60, enabled: false })
const hfishSaving = ref(false)
const hfishSyncing = ref(false)
const hfishMsg = ref('')
const hfishMsgOk = ref(true)

// ── Nmap 状态 ──
const nmapConfig = ref({ nmap_path: null as string | null, ip_ranges: [] as string[], scan_interval: 604800, enabled: false })
const nmapForm = reactive({ nmap_path: '', scan_interval: 604800, enabled: false })
const nmapIpRangesText = ref('')
const nmapSaving = ref(false)
const nmapMsg = ref('')
const nmapMsgOk = ref(true)

// ── 防火墙同步配置 ──
const firewallConfig = ref<FirewallConfig>({
  enabled: true,
  api_base_url: null,
  default_vendor: 'generic',
  default_policy_id: null,
  timeout_seconds: 10,
  has_custom_sign_secret: false,
})
const firewallForm = reactive({
  enabled: true,
  api_base_url: '',
  default_vendor: 'generic',
  default_policy_id: '',
  timeout_seconds: 10,
  sign_secret: '',
})
const firewallSaving = ref(false)
const firewallMsg = ref('')
const firewallMsgOk = ref(true)

// ── AI API 配置 ──
const aiApiConfig = ref<AIAPIConfig>({
  provider: 'ollama',
  base_url: 'http://localhost:11434',
  model_name: 'llama2',
  enabled: true,
  api_key_configured: false,
})
const aiApiForm = reactive({
  provider: 'ollama',
  base_url: 'http://localhost:11434',
  model_name: 'llama2',
  api_key: '',
  enabled: true,
})
const aiApiSaving = ref(false)
const aiApiMsg = ref('')
const aiApiMsgOk = ref(true)

// ── TTS 语音配置 ──
const ttsEngineConfig = ref<TTSConfig>({
  provider: 'local',
  endpoint: null,
  model_name: 'local-tts-v1',
  voice_model: 'local-tts-v1',
  enabled: true,
})
const ttsEngineForm = reactive({
  provider: 'local',
  endpoint: '',
  model_name: 'local-tts-v1',
  voice_model: 'local-tts-v1',
  enabled: true,
})
const ttsEngineSaving = ref(false)
const ttsEngineMsg = ref('')
const ttsEngineMsgOk = ref(true)

const normalizeAIApiConfig = (cfg?: Partial<AIAPIConfig> | null): AIAPIConfig => ({
  provider: cfg?.provider || 'ollama',
  base_url: cfg?.base_url || 'http://localhost:11434',
  model_name: cfg?.model_name || 'llama2',
  enabled: cfg?.enabled ?? true,
  api_key_configured: Boolean(cfg?.api_key_configured),
})

const normalizeTTSConfig = (cfg?: Partial<TTSConfig> | null): TTSConfig => ({
  provider: cfg?.provider || 'local',
  endpoint: cfg?.endpoint ?? null,
  model_name: cfg?.model_name || 'local-tts-v1',
  voice_model: cfg?.voice_model || cfg?.model_name || 'local-tts-v1',
  enabled: cfg?.enabled ?? true,
})

const normalizePushChannel = (value: unknown): PushChannel | null => {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, any>
  const id = Number(record.id)
  if (!Number.isFinite(id)) return null
  return {
    id,
    channel_type: typeof record.channel_type === 'string' && record.channel_type.trim() ? record.channel_type : 'webhook',
    channel_name: typeof record.channel_name === 'string' && record.channel_name.trim() ? record.channel_name : `channel-${id}`,
    target: typeof record.target === 'string' ? record.target : '',
    enabled: record.enabled === true || Number(record.enabled) === 1 ? 1 : 0,
  }
}

const normalizeCredential = (value: unknown): DeviceCredential | null => {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, any>
  const id = Number(record.id)
  const deviceId = Number(record.device_id)
  if (!Number.isFinite(id) || !Number.isFinite(deviceId)) return null
  return {
    id,
    device_id: deviceId,
    username: typeof record.username === 'string' ? record.username : '',
    created_at: typeof record.created_at === 'string' ? record.created_at : null,
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
  }
}

const normalizeDevice = (value: unknown): DeviceInfo | null => {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, any>
  const id = Number(record.id)
  const port = Number(record.port)
  if (!Number.isFinite(id)) return null
  return {
    id,
    name: typeof record.name === 'string' ? record.name : `device-${id}`,
    ip: typeof record.ip === 'string' ? record.ip : '',
    port: Number.isFinite(port) ? port : 22,
    vendor: typeof record.vendor === 'string' && record.vendor.trim() ? record.vendor : 'generic',
    device_type: typeof record.device_type === 'string' ? record.device_type : null,
    enabled: Boolean(record.enabled ?? true),
    description: typeof record.description === 'string' ? record.description : null,
    credentials: Array.isArray(record.credentials)
      ? record.credentials.map(normalizeCredential).filter((item): item is DeviceCredential => item !== null)
      : [],
    created_at: typeof record.created_at === 'string' ? record.created_at : null,
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
  }
}

interface PromptDialogField {
  key: string
  label: string
  type: 'text' | 'password'
  placeholder?: string
  value: string
}

const promptDialog = reactive({
  open: false,
  title: '',
  description: '',
  confirmLabel: '确定',
  fields: [] as PromptDialogField[],
  resolver: null as null | ((value: Record<string, string> | null) => void),
})

const confirmDialog = reactive({
  open: false,
  title: '',
  description: '',
  confirmLabel: '确认',
  resolver: null as null | ((value: boolean) => void),
})

const closePromptDialog = (value: Record<string, string> | null) => {
  promptDialog.open = false
  const resolver = promptDialog.resolver
  promptDialog.resolver = null
  resolver?.(value)
}

const handlePromptDialogToggle = (open: boolean) => {
  if (!open && promptDialog.open) {
    closePromptDialog(null)
    return
  }
  promptDialog.open = open
}

const openPromptDialog = (config: {
  title: string
  description: string
  confirmLabel?: string
  fields: Array<Omit<PromptDialogField, 'value'> & { value?: string }>
}) => new Promise<Record<string, string> | null>((resolve) => {
  promptDialog.title = config.title
  promptDialog.description = config.description
  promptDialog.confirmLabel = config.confirmLabel || '确定'
  promptDialog.fields = config.fields.map(field => ({
    ...field,
    value: field.value ?? '',
  }))
  promptDialog.resolver = resolve
  promptDialog.open = true
})

const submitPromptDialog = () => {
  const values = promptDialog.fields.reduce<Record<string, string>>((acc, field) => {
    acc[field.key] = field.value
    return acc
  }, {})
  closePromptDialog(values)
}

const closeConfirmDialog = (value: boolean) => {
  confirmDialog.open = false
  const resolver = confirmDialog.resolver
  confirmDialog.resolver = null
  resolver?.(value)
}

const handleConfirmDialogToggle = (open: boolean) => {
  if (!open && confirmDialog.open) {
    closeConfirmDialog(false)
    return
  }
  confirmDialog.open = open
}

const openConfirmDialog = (config: { title: string; description: string; confirmLabel?: string }) => new Promise<boolean>((resolve) => {
  confirmDialog.title = config.title
  confirmDialog.description = config.description
  confirmDialog.confirmLabel = config.confirmLabel || '确认'
  confirmDialog.resolver = resolve
  confirmDialog.open = true
})

const showMsg = (msgRef: typeof hfishMsg, okRef: typeof hfishMsgOk, msg: string, ok: boolean) => {
  msgRef.value = msg
  okRef.value = ok
  setTimeout(() => { msgRef.value = '' }, 3000)
}

const loadHFishConfig = async () => {
  try {
    const cfg = await defenseApi.getHFishConfig()
    if (!cfg) return
    hfishConfig.value = {
      host_port: cfg.host_port ?? null,
      api_base_url: cfg.api_base_url ?? null,
      sync_interval: cfg.sync_interval ?? 60,
      enabled: Boolean(cfg.enabled),
    }
    hfishForm.host_port = cfg.host_port ?? ''
    hfishForm.api_base_url = cfg.api_base_url ?? ''
    hfishForm.api_key = ''
    hfishForm.sync_interval = cfg.sync_interval ?? 60
    hfishForm.enabled = Boolean(cfg.enabled)
  } catch {
    // 配置可能未初始化，忽略
  }
}

const loadNmapConfig = async () => {
  try {
    const cfg = await scanApi.getNmapConfig()
    if (!cfg) return
    nmapConfig.value = {
      nmap_path: cfg.nmap_path ?? null,
      ip_ranges: Array.isArray(cfg.ip_ranges) ? cfg.ip_ranges : [],
      scan_interval: cfg.scan_interval ?? 604800,
      enabled: Boolean(cfg.enabled),
    }
    nmapForm.nmap_path = cfg.nmap_path ?? ''
    nmapForm.scan_interval = cfg.scan_interval ?? 604800
    nmapForm.enabled = Boolean(cfg.enabled)
    nmapIpRangesText.value = Array.isArray(cfg.ip_ranges) ? cfg.ip_ranges.join('\n') : ''
  } catch {
    // 未初始化忽略
  }
}

const loadFirewallConfig = async () => {
  try {
    const cfg = await firewallApi.getConfig()
    if (!cfg) return
    firewallConfig.value = {
      enabled: cfg.enabled ?? true,
      api_base_url: cfg.api_base_url ?? null,
      default_vendor: cfg.default_vendor || 'generic',
      default_policy_id: cfg.default_policy_id ?? null,
      timeout_seconds: cfg.timeout_seconds || 10,
      has_custom_sign_secret: cfg.has_custom_sign_secret ?? false,
    }
    firewallForm.enabled = cfg.enabled ?? true
    firewallForm.api_base_url = cfg.api_base_url ?? ''
    firewallForm.default_vendor = cfg.default_vendor || 'generic'
    firewallForm.default_policy_id = cfg.default_policy_id ?? ''
    firewallForm.timeout_seconds = cfg.timeout_seconds || 10
    firewallForm.sign_secret = ''
  } catch {
    // 未初始化忽略
  }
}

const saveFirewallConfig = async () => {
  if (!firewallForm.default_vendor.trim()) {
    showMsg(firewallMsg, firewallMsgOk, '请填写默认厂商', false)
    return
  }
  firewallSaving.value = true
  try {
    await firewallApi.saveConfig({
      enabled: firewallForm.enabled,
      api_base_url: firewallForm.api_base_url.trim(),
      default_vendor: firewallForm.default_vendor.trim(),
      default_policy_id: firewallForm.default_policy_id.trim(),
      timeout_seconds: firewallForm.timeout_seconds,
      sign_secret: firewallForm.sign_secret.trim() || undefined,
    })
    firewallForm.sign_secret = ''
    await loadFirewallConfig()
    showMsg(firewallMsg, firewallMsgOk, '防火墙配置已保存', true)
  } catch (e: any) {
    showMsg(firewallMsg, firewallMsgOk, e?.response?.data?.detail || '保存失败', false)
  } finally {
    firewallSaving.value = false
  }
}

const loadAIApiConfig = async () => {
  try {
    const cfg = normalizeAIApiConfig(await systemApi.getAIConfig())
    aiApiConfig.value = cfg
    aiApiForm.provider = cfg.provider
    aiApiForm.base_url = cfg.base_url
    aiApiForm.model_name = cfg.model_name
    aiApiForm.api_key = ''
    aiApiForm.enabled = cfg.enabled
  } catch {
    aiApiConfig.value = normalizeAIApiConfig()
  }
}

const saveAIApiConfig = async () => {
  if (!aiApiForm.base_url.trim()) {
    showMsg(aiApiMsg, aiApiMsgOk, '请填写 AI API 地址', false)
    return
  }
  if (!aiApiForm.model_name.trim()) {
    showMsg(aiApiMsg, aiApiMsgOk, '请填写模型名称', false)
    return
  }
  aiApiSaving.value = true
  try {
    const cfg = await systemApi.saveAIConfig({
      provider: aiApiForm.provider.trim() || 'ollama',
      base_url: aiApiForm.base_url.trim(),
      model_name: aiApiForm.model_name.trim(),
      api_key: aiApiForm.api_key.trim() || undefined,
      enabled: aiApiForm.enabled,
    })
    aiApiConfig.value = normalizeAIApiConfig(cfg)
    aiApiForm.api_key = ''
    showMsg(aiApiMsg, aiApiMsgOk, 'AI API 配置已保存', true)
  } catch (e: any) {
    if (e?.response?.status === 404) {
      showMsg(aiApiMsg, aiApiMsgOk, '后端未加载 AI API 配置接口，请重启后端服务后重试', false)
    } else {
      showMsg(aiApiMsg, aiApiMsgOk, getRequestErrorMessage(e, '保存失败'), false)
    }
  } finally {
    aiApiSaving.value = false
  }
}

const loadTTSConfig = async () => {
  try {
    const cfg = normalizeTTSConfig(await systemApi.getTTSConfig())
    ttsEngineConfig.value = cfg
    ttsEngineForm.provider = cfg.provider
    ttsEngineForm.endpoint = cfg.endpoint ?? ''
    ttsEngineForm.model_name = cfg.model_name
    ttsEngineForm.voice_model = cfg.voice_model
    ttsEngineForm.enabled = cfg.enabled
  } catch {
    ttsEngineConfig.value = normalizeTTSConfig()
  }
}

const saveTTSConfig = async () => {
  if (!ttsEngineForm.model_name.trim()) {
    showMsg(ttsEngineMsg, ttsEngineMsgOk, '请填写 TTS 模型名称', false)
    return
  }
  ttsEngineSaving.value = true
  try {
    const cfg = await systemApi.saveTTSConfig({
      provider: ttsEngineForm.provider.trim() || 'local',
      endpoint: ttsEngineForm.endpoint.trim() || undefined,
      model_name: ttsEngineForm.model_name.trim(),
      voice_model: ttsEngineForm.voice_model.trim() || undefined,
      enabled: ttsEngineForm.enabled,
    })
    ttsEngineConfig.value = normalizeTTSConfig(cfg)
    showMsg(ttsEngineMsg, ttsEngineMsgOk, 'TTS 配置已保存', true)
  } catch (e: any) {
    if (e?.response?.status === 404) {
      showMsg(ttsEngineMsg, ttsEngineMsgOk, '后端未加载 TTS 配置接口，请重启后端服务后重试', false)
    } else {
      showMsg(ttsEngineMsg, ttsEngineMsgOk, getRequestErrorMessage(e, '保存失败'), false)
    }
  } finally {
    ttsEngineSaving.value = false
  }
}

const saveHFishConfig = async () => {
  if (!hfishForm.host_port.trim()) {
    showMsg(hfishMsg, hfishMsgOk, '请填写 HFish 地址', false)
    return
  }
  hfishSaving.value = true
  try {
    await defenseApi.saveHFishConfig({
      host_port: hfishForm.host_port.trim(),
      api_key: hfishForm.api_key || '',
      sync_interval: hfishForm.sync_interval,
      enabled: hfishForm.enabled,
      api_base_url: hfishForm.api_base_url.trim() || undefined,
    })
    hfishConfig.value.enabled = hfishForm.enabled
    showMsg(hfishMsg, hfishMsgOk, '配置已保存', true)
  } catch (e: any) {
    showMsg(hfishMsg, hfishMsgOk, e?.response?.data?.detail || '保存失败', false)
  } finally {
    hfishSaving.value = false
  }
}

const triggerHFishSync = async () => {
  hfishSyncing.value = true
  try {
    const res: any = await defenseApi.triggerHFishSync()
    showMsg(hfishMsg, hfishMsgOk, res?.data?.message || '同步完成', true)
  } catch (e: any) {
    showMsg(hfishMsg, hfishMsgOk, e?.response?.data?.detail || '同步失败', false)
  } finally {
    hfishSyncing.value = false
  }
}

const saveNmapConfig = async () => {
  if (!nmapForm.nmap_path.trim()) {
    showMsg(nmapMsg, nmapMsgOk, '请填写 Nmap 路径', false)
    return
  }
  const ipRanges = nmapIpRangesText.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (ipRanges.length === 0) {
    showMsg(nmapMsg, nmapMsgOk, '请填写至少一个扫描目标', false)
    return
  }
  nmapSaving.value = true
  try {
    await scanApi.saveNmapConfig({
      nmap_path: nmapForm.nmap_path.trim(),
      ip_ranges: ipRanges,
      scan_interval: nmapForm.scan_interval,
      enabled: nmapForm.enabled,
    })
    nmapConfig.value.enabled = nmapForm.enabled
    showMsg(nmapMsg, nmapMsgOk, '配置已保存', true)
  } catch (e: any) {
    showMsg(nmapMsg, nmapMsgOk, e?.response?.data?.detail || '保存失败', false)
  } finally {
    nmapSaving.value = false
  }
}

// ── 漏洞脚本规则 ──
const vulnScriptsMap = ref<Record<string, string[]>>({})
const vulnMsg = ref('')
const vulnMsgOk = ref(true)

const DEFAULT_VULN_SCRIPTS: Record<string, string[]> = {
  linux: ['ftp-anon', 'ssh-vuln-openssh'],
  win10: ['smb-vuln-ms17-010'],
  win7: ['smb-vuln-ms17-010', 'smb-vuln-ms08-067'],
  windows: ['smb-vuln-ms17-010', 'smb-vuln-ms08-067'],
}

const loadVulnScripts = async () => {
  try {
    const cfg = await scanApi.getNmapConfig()
    const map = (cfg as any).vuln_scripts_by_tag
    if (map && typeof map === 'object') {
      vulnScriptsMap.value = JSON.parse(JSON.stringify(map))
    } else {
      vulnScriptsMap.value = JSON.parse(JSON.stringify(DEFAULT_VULN_SCRIPTS))
    }
  } catch {
    vulnScriptsMap.value = JSON.parse(JSON.stringify(DEFAULT_VULN_SCRIPTS))
  }
}

const addVulnTag = async () => {
  const result = await openPromptDialog({
    title: '添加系统标签',
    description: '请输入系统标签，例如 linux、win7、ubuntu。',
    confirmLabel: '添加',
    fields: [
      { key: 'tag', label: '系统标签', type: 'text', placeholder: 'linux' },
    ],
  })
  const tag = result?.tag?.trim()
  if (tag && !vulnScriptsMap.value[tag]) {
    vulnScriptsMap.value[tag] = []
  }
}

const removeVulnTag = (tag: string) => {
  const map = { ...vulnScriptsMap.value }
  delete map[tag]
  vulnScriptsMap.value = map
}

const addScript = async (tag: string) => {
  const result = await openPromptDialog({
    title: '添加漏洞脚本',
    description: `为标签 ${tag} 添加 Nmap 漏洞脚本。`,
    confirmLabel: '添加',
    fields: [
      { key: 'script', label: '脚本名', type: 'text', placeholder: 'smb-vuln-ms17-010' },
    ],
  })
  const script = result?.script?.trim()
  if (script) {
    vulnScriptsMap.value = {
      ...vulnScriptsMap.value,
      [tag]: [...(vulnScriptsMap.value[tag] || []), script],
    }
  }
}

const removeScript = (tag: string, idx: number) => {
  vulnScriptsMap.value = {
    ...vulnScriptsMap.value,
    [tag]: vulnScriptsMap.value[tag].filter((_, i) => i !== idx),
  }
}

const saveVulnScripts = async () => {
  nmapSaving.value = true
  try {
    const ipRanges = nmapIpRangesText.value.split('\n').map(s => s.trim()).filter(Boolean)
    await scanApi.saveNmapConfig({
      nmap_path: nmapForm.nmap_path.trim() || 'nmap',
      ip_ranges: ipRanges.length ? ipRanges : nmapConfig.value.ip_ranges,
      scan_interval: nmapForm.scan_interval,
      enabled: nmapForm.enabled,
      vuln_scripts_by_tag: vulnScriptsMap.value,
    })
    vulnMsg.value = '漏洞规则已保存'
    vulnMsgOk.value = true
  } catch (e: any) {
    vulnMsg.value = e?.response?.data?.detail || '保存失败'
    vulnMsgOk.value = false
  } finally {
    nmapSaving.value = false
    setTimeout(() => { vulnMsg.value = '' }, 3000)
  }
}

// ── 推送通道 ──
interface PushChannel {
  id: number
  channel_type: string
  channel_name: string
  target: string
  enabled: number
}

const channels = ref<PushChannel[]>([])
const channelsLoading = ref(false)
const showAddChannel = ref(false)
const channelCreating = ref(false)
const channelMsg = ref('')
const channelMsgOk = ref(true)
const channelForm = reactive({
  channel_type: 'webhook',
  channel_name: '',
  target: '',
})

const isRenderablePushChannel = (value: unknown): value is PushChannel => {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return (
    Number.isFinite(Number(record.id)) &&
    typeof record.channel_type === 'string' &&
    typeof record.channel_name === 'string' &&
    typeof record.target === 'string' &&
    (Number(record.enabled) === 0 || Number(record.enabled) === 1)
  )
}

const safeChannels = computed(() => channels.value.filter(isRenderablePushChannel))

const loadChannels = async () => {
  channelsLoading.value = true
  try {
    const res: any = await apiClient.get('/push/channels')
    const data = res?.data ?? res
    const list: unknown[] = Array.isArray(data) ? data : (Array.isArray(data?.items) ? data.items : [])
    channels.value = list
      .map(normalizePushChannel)
      .filter((item): item is PushChannel => isRenderablePushChannel(item))
  } catch {
    channels.value = []
  } finally {
    channelsLoading.value = false
  }
}

const createChannel = async () => {
  if (!channelForm.channel_name.trim() || !channelForm.target.trim()) {
    channelMsg.value = '请填写完整'
    channelMsgOk.value = false
    setTimeout(() => { channelMsg.value = '' }, 3000)
    return
  }
  channelCreating.value = true
  channelMsg.value = ''
  try {
    await apiClient.post('/push/channels', { ...channelForm })
    channelMsgOk.value = true
    channelMsg.value = '创建成功'
    showAddChannel.value = false
    channelForm.channel_name = ''
    channelForm.target = ''
    await loadChannels()
  } catch (e: any) {
    channelMsgOk.value = false
    channelMsg.value = e?.displayMessage || '创建失败'
  } finally {
    channelCreating.value = false
    setTimeout(() => { channelMsg.value = '' }, 3000)
  }
}

const toggleChannel = async (ch: PushChannel) => {
  try {
    await apiClient.put(`/push/channels/${ch.id}`, { enabled: ch.enabled ? 0 : 1 })
    await loadChannels()
  } catch { /* ignore */ }
}

const testChannel = async (id: number) => {
  try {
    await apiClient.post(`/push/channels/${id}/test`)
    channelMsg.value = '测试推送已完成'
    channelMsgOk.value = true
  } catch {
    channelMsg.value = '测试失败'
    channelMsgOk.value = false
  }
  setTimeout(() => { channelMsg.value = '' }, 3000)
}

const deleteChannel = async (id: number) => {
  try {
    await apiClient.delete(`/push/channels/${id}`)
    await loadChannels()
  } catch { /* ignore */ }
}

// ── 设备凭证管理 ──
const devices = ref<DeviceInfo[]>([])
const devicesLoading = ref(false)
const showAddDevice = ref(false)
const deviceCreating = ref(false)
const deviceMsg = ref('')
const deviceMsgOk = ref(true)
const deviceForm = reactive({
  name: '',
  ip: '',
  port: 22,
  vendor: 'huawei',
  device_type: '',
  description: '',
})

const isRenderableDevice = (value: unknown): value is DeviceInfo => {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return (
    Number.isFinite(Number(record.id)) &&
    typeof record.name === 'string' &&
    typeof record.ip === 'string' &&
    Number.isFinite(Number(record.port)) &&
    typeof record.vendor === 'string' &&
    typeof record.enabled === 'boolean'
  )
}

const safeDevices = computed(() => devices.value.filter(isRenderableDevice))

const showDeviceMsg = (msg: string, ok: boolean) => {
  deviceMsg.value = msg
  deviceMsgOk.value = ok
  setTimeout(() => { deviceMsg.value = '' }, 3000)
}

const loadDevices = async () => {
  devicesLoading.value = true
  try {
    const data = await deviceApi.list()
    const list: unknown[] = Array.isArray(data) ? data : (Array.isArray((data as any)?.items) ? (data as any).items : [])
    devices.value = list
      .map(normalizeDevice)
      .filter((item): item is DeviceInfo => isRenderableDevice(item))
  } catch {
    devices.value = []
  } finally {
    devicesLoading.value = false
  }
}

const createDevice = async () => {
  if (!deviceForm.name.trim() || !deviceForm.ip.trim() || !deviceForm.vendor) {
    showDeviceMsg('请填写设备名称、IP 和厂商', false)
    return
  }
  deviceCreating.value = true
  try {
    await deviceApi.create({
      name: deviceForm.name.trim(),
      ip: deviceForm.ip.trim(),
      port: deviceForm.port,
      vendor: deviceForm.vendor,
      device_type: deviceForm.device_type.trim() || undefined,
      description: deviceForm.description.trim() || undefined,
    })
    showDeviceMsg('设备已创建', true)
    showAddDevice.value = false
    deviceForm.name = ''
    deviceForm.ip = ''
    deviceForm.port = 22
    deviceForm.device_type = ''
    deviceForm.description = ''
    await loadDevices()
  } catch (e: any) {
    showDeviceMsg(e?.displayMessage || '创建失败', false)
  } finally {
    deviceCreating.value = false
  }
}

const toggleDevice = async (dev: DeviceInfo) => {
  try {
    await deviceApi.update(dev.id, { enabled: !dev.enabled })
    await loadDevices()
  } catch { /* ignore */ }
}

const removeDevice = async (id: number) => {
  const confirmed = await openConfirmDialog({
    title: '删除设备',
    description: '确定删除该设备及所有关联凭证吗？',
    confirmLabel: '删除',
  })
  if (!confirmed) return
  try {
    await deviceApi.remove(id)
    await loadDevices()
  } catch { /* ignore */ }
}

const promptAddCredential = async (deviceId: number) => {
  const result = await openPromptDialog({
    title: '添加凭证',
    description: '输入设备登录用户名和密码。',
    confirmLabel: '保存',
    fields: [
      { key: 'username', label: '用户名', type: 'text', placeholder: 'admin' },
      { key: 'password', label: '密码', type: 'password', placeholder: '请输入密码' },
    ],
  })
  const username = result?.username?.trim()
  const password = result?.password ?? ''
  if (!username || !password) return
  try {
    await deviceApi.addCredential(deviceId, username, password)
    await loadDevices()
  } catch (e: any) {
    showDeviceMsg(e?.displayMessage || '添加凭证失败', false)
  }
}

const promptUpdateCredential = async (deviceId: number, cred: DeviceCredential) => {
  const result = await openPromptDialog({
    title: '修改凭证',
    description: '用户名留空表示不修改，密码留空表示保持原值。',
    confirmLabel: '保存',
    fields: [
      { key: 'username', label: '用户名', type: 'text', value: cred.username },
      { key: 'password', label: '新密码', type: 'password', placeholder: '留空则不修改' },
    ],
  })
  if (!result) return
  const username = result.username?.trim() || ''
  const password = result.password ?? ''
  const payload: { username?: string; password?: string } = {}
  if (username && username !== cred.username) payload.username = username
  if (password) payload.password = password
  if (Object.keys(payload).length === 0) return
  try {
    await deviceApi.updateCredential(deviceId, cred.id, payload)
    await loadDevices()
  } catch (e: any) {
    showDeviceMsg(e?.displayMessage || '修改凭证失败', false)
  }
}

const removeCredential = async (deviceId: number, credId: number) => {
  const confirmed = await openConfirmDialog({
    title: '删除凭证',
    description: '确定删除该凭证吗？',
    confirmLabel: '删除',
  })
  if (!confirmed) return
  try {
    await deviceApi.removeCredential(deviceId, credId)
    await loadDevices()
  } catch { /* ignore */ }
}

onMounted(() => {
  if (!hasAccessToken()) {
    return
  }
  loadAIApiConfig()
  loadTTSConfig()
  loadHFishConfig()
  loadNmapConfig()
  loadFirewallConfig()
  loadChannels()
  loadVulnScripts()
  loadDevices()
})
</script>
