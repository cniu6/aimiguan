"""AI Engine Service - 核心 AI 逻辑"""
import os
import json
from typing import Dict, Any, Optional
import httpx

class LocalLLMClient:
    """本地 LLM 客户端（支持 Ollama / LocalAI）"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama2")
    
    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """生成 AI 响应"""
        # Implement actual LLM API call (Ollama/LocalAI)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                
                if system:
                    payload["system"] = system
                
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()
                
                # Ollama response format: {"response": "...", "done": true}
                # LocalAI response format may differ
                if "response" in result:
                    return result["response"]
                elif "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0].get("message", {}).get("content", "")
                else:
                    return str(result)
        except httpx.HTTPStatusError as e:
            print(f"LLM API error: {e}")
            return f"AI服务暂时不可用: {str(e)}"
        except Exception as e:
            print(f"LLM error: {e}")
            return f"AI服务异常: {str(e)}"
            print(f"LLM API error: {e}")
            return f"AI服务暂时不可用: {str(e)}"
        except Exception as e:
            print(f"LLM error: {e}")
            return f"AI服务异常: {str(e)}"
        # Placeholder implementation
        return f"AI response to: {prompt[:50]}..."
    
    async def generate_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        """生成 JSON 格式响应"""
        # Implement JSON mode generation
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                }
                
                if system:
                    payload["system"] = system
                
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()
                
                # Try to parse JSON from response
                if "response" in result:
                    try:
                        import json as json_module
                        return json_module.loads(result["response"])
                    except json_module.JSONDecodeError:
                        pass
                
                # Fallback: return dict with raw response
                return {"response": result.get("response", str(result))}
        except Exception as e:
            print(f"JSON generation error: {e}")
            return {"response": f"AI服务异常: {str(e)}"}

class AIEngine:
    """AI 引擎 - 风险评估、扫描分析、报告生成"""
    
    def __init__(self):
        self.llm_client = LocalLLMClient()
    
    async def assess_threat(self, ip: str, attack_type: str, attack_count: int, history: Optional[str] = None) -> Dict[str, Any]:
        """风险评估"""
        prompt = f"""
分析以下威胁事件并给出风险评分：
- 攻击者 IP: {ip}
- 攻击类型: {attack_type}
- 攻击次数: {attack_count}
- 历史行为: {history or '无'}

请以 JSON 格式返回：
{{
  "score": 0-100,
  "reason": "评估理由",
  "action_suggest": "BLOCK" 或 "MONITOR"
}}
"""
        
        # Call LLM and parse response
        # Placeholder logic
        score = min(50 + attack_count * 10, 100)
        action = "BLOCK" if score >= 80 else "MONITOR"
        
        # Call AI engine for risk assessment
        try:
            ai_response = await self.llm_client.generate_json(prompt, system="你是一个安全分析助手，返回JSON格式的风险评估。")
            
            # Parse AI response
            response_text = ai_response.get("response", "")
            
            # Try to extract score from JSON response
            if "score" in ai_response:
                score = ai_response.get("score", 50)
            elif isinstance(ai_response, dict) and "response" in ai_response:
                try:
                    parsed = json.loads(ai_response.get("response", "{}"))
                    score = parsed.get("score", 50)
                except:
                    pass
            
            # Determine action based on score
            if score >= 80:
                action = "BLOCK"
            else:
                action = "MONITOR"
            
            reason = ai_response.get("response", f"基于 {attack_count} 次攻击评估，来自 {ip}")
            
            return {
                "score": min(max(score, 0), 100),
                "reason": reason[:200],
                "action_suggest": action
            }
        except Exception as e:
            print(f"AI risk assessment error: {e}")
            # Fallback to rule-based scoring
            score = min(50 + attack_count * 10, 100)
            action = "BLOCK" if score >= 80 else "MONITOR"
            return {
                "score": score,
                "reason": f"检测到 {attack_count} 次攻击，来自 {ip} (规则降级)",
                "action_suggest": action
            }
    async def analyze_scan_result(self, scan_data: Dict[str, Any]) -> str:
        """扫描结果分析"""
        prompt = f"""
分析以下 Nmap 扫描结果并生成 Markdown 格式的风险分析报告：

{json.dumps(scan_data, indent=2)}

请包含：
1. 开放端口风险评估
2. 服务版本漏洞分析
3. 修复建议
"""
        
        # TODO: Call LLM for analysis
        return "## 扫描结果分析\n\n暂未实现 AI 分析功能"
    
    async def generate_report(self, report_type: str, data: Dict[str, Any]) -> str:
        """生成报告"""
        prompt = f"""
生成 {report_type} 报告，数据如下：
{json.dumps(data, indent=2)}

请生成 Markdown 格式的专业报告。
"""
        
        # TODO: Call LLM for report generation
        return f"# {report_type} 报告\n\n暂未实现报告生成功能"
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """多轮对话"""
        system_prompt = "你是一个安全运营助手，帮助用户分析威胁事件和扫描结果。"
        
        if context:
            system_prompt += f"\n\n当前上下文：{json.dumps(context, ensure_ascii=False)}"
        
        response = await self.llm_client.generate(message, system=system_prompt)
        return response

# Global instance
ai_engine = AIEngine()