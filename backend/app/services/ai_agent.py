"""
AI Agent service for trend analysis and recommendations
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import os
import json
from anthropic import Anthropic

client = Anthropic()


class AIAgentService:
    """Service for AI-powered trend analysis and recommendations"""
    
    def __init__(self):
        self.model = "claude-3-5-sonnet-20241022"  # Latest Claude model
    
    def build_prompt(self, 
                    symbol: str,
                    current_price: float,
                    indicators: Dict[str, Any],
                    risk_profile: Optional[Dict[str, Any]] = None,
                    feedback_history: Optional[List[Dict[str, Any]]] = None,
                    news_context: Optional[List[str]] = None) -> str:
        """
        Build the prompt for the LLM
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            indicators: Dict of calculated indicators
            risk_profile: User's risk profile
            feedback_history: Past analysis outcomes
            news_context: Recent news headlines
            
        Returns:
            Formatted prompt string
        """
        
        prompt = f"""You are an investment analysis assistant. Analyze the following stock and provide insights.

STOCK ANALYSIS REQUEST
======================
Symbol: {symbol}
Current Price: ₹{current_price:.2f}

TECHNICAL INDICATORS
====================
"""
        
        # Add indicators
        if indicators:
            if indicators.get("rsi_14"):
                prompt += f"RSI (14): {indicators['rsi_14']:.2f}\n"
            if indicators.get("sma_20"):
                prompt += f"SMA (20): ₹{indicators['sma_20']:.2f}\n"
            if indicators.get("sma_50"):
                prompt += f"SMA (50): ₹{indicators['sma_50']:.2f}\n"
            if indicators.get("ema_20"):
                prompt += f"EMA (20): ₹{indicators['ema_20']:.2f}\n"
            if indicators.get("volatility"):
                prompt += f"Realized Volatility (20d): {indicators['volatility']:.2f}%\n"
            if indicators.get("pct_change"):
                prompt += f"Recent % Change: {indicators['pct_change']:.2f}%\n"
            if indicators.get("bollinger_bands"):
                bb = indicators["bollinger_bands"]
                prompt += f"Bollinger Bands: Lower ₹{bb['lower']:.2f} | Mid ₹{bb['middle']:.2f} | Upper ₹{bb['upper']:.2f}\n"
            if indicators.get("macd"):
                macd = indicators["macd"]
                prompt += f"MACD: {macd['macd']:.2f} | Signal: {macd['signal']:.2f} | Histogram: {macd['histogram']:.2f}\n"
        
        # Add user risk profile
        if risk_profile:
            prompt += f"\nUSER RISK PROFILE\n"
            prompt += f"================\n"
            if risk_profile.get("time_horizon"):
                prompt += f"Time Horizon: {risk_profile['time_horizon']}\n"
            if risk_profile.get("loss_tolerance"):
                prompt += f"Loss Tolerance: {risk_profile['loss_tolerance']}\n"
            if risk_profile.get("experience_level"):
                prompt += f"Experience Level: {risk_profile['experience_level']}\n"
        
        # Add feedback history for adaptability
        if feedback_history:
            prompt += f"\nPAST ANALYSIS FEEDBACK (Last 5 Analyses)\n"
            prompt += f"=========================================\n"
            for feedback in feedback_history[-5:]:
                flag_useful = "Useful" if feedback.get("was_flag_useful") else "Not Useful"
                pct = feedback.get("outcome_pct_change", 0)
                prompt += f"- Flag was {flag_useful}: Stock moved {pct:+.2f}%\n"
        
        # Add news context
        if news_context:
            prompt += f"\nRECENT NEWS\n"
            prompt += f"===========\n"
            for headline in news_context[:5]:
                prompt += f"- {headline}\n"
        
        # Add instructions
        prompt += f"""
ANALYSIS INSTRUCTIONS
=====================
1. Provide a plain-language trend summary (2-3 sentences)
2. Identify the risk level relative to the user's risk profile: low, medium, or high
3. Explain your reasoning clearly
4. Provide caveats and confidence notes
5. Do NOT provide direct buy/sell instructions - educational framing only
6. Format your response as JSON with the following structure:

{{
    "trend_summary": "Plain language summary of the trend",
    "risk_flag": "low|medium|high",
    "reasoning": "Detailed explanation of analysis",
    "caveats": "Important caveats and confidence notes",
    "technical_outlook": "Brief technical outlook based on indicators",
    "confidence_score": 0.5
}}

Important: This analysis is for educational purposes only. Always do your own research and consult financial advisors before making investment decisions.
"""
        
        return prompt
    
    def analyze_symbol(self,
                      symbol: str,
                      current_price: float,
                      indicators: Dict[str, Any],
                      risk_profile: Optional[Dict[str, Any]] = None,
                      feedback_history: Optional[List[Dict[str, Any]]] = None,
                      news_context: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a symbol using Claude LLM
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            indicators: Calculated indicators
            risk_profile: User's risk profile
            feedback_history: Past analysis outcomes
            news_context: Recent news
            
        Returns:
            Dict with analysis result or None
        """
        try:
            prompt = self.build_prompt(
                symbol=symbol,
                current_price=current_price,
                indicators=indicators,
                risk_profile=risk_profile,
                feedback_history=feedback_history,
                news_context=news_context
            )
            
            # Call Claude API
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            
            # Try to parse as JSON
            try:
                # Find JSON in response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    # If no JSON found, create a basic response
                    analysis = {
                        "trend_summary": response_text,
                        "risk_flag": "medium",
                        "reasoning": response_text,
                        "caveats": "Unable to parse structured response",
                        "technical_outlook": "",
                        "confidence_score": 0.5
                    }
            except json.JSONDecodeError:
                analysis = {
                    "trend_summary": response_text,
                    "risk_flag": "medium",
                    "reasoning": response_text,
                    "caveats": "Unable to parse structured response",
                    "technical_outlook": "",
                    "confidence_score": 0.5
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"AI analysis error for {symbol}: {e}")
            return None
    
    def generate_default_analysis(self, symbol: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a basic analysis if LLM call fails
        
        Args:
            symbol: Stock symbol
            indicators: Calculated indicators
            
        Returns:
            Dict with basic analysis
        """
        rsi = indicators.get("rsi_14", 50)
        volatility = indicators.get("volatility", 0)
        pct_change = indicators.get("pct_change", 0)
        
        # Determine risk flag based on indicators
        if rsi > 70 or volatility > 30:
            risk_flag = "high"
        elif rsi < 30 or volatility > 20:
            risk_flag = "medium"
        else:
            risk_flag = "low"
        
        # Determine trend
        if pct_change > 5:
            trend = f"showing strong upward momentum with {pct_change:.2f}% recent gain"
        elif pct_change < -5:
            trend = f"showing downward pressure with {pct_change:.2f}% recent loss"
        else:
            trend = f"trading relatively flat with {pct_change:.2f}% recent change"
        
        return {
            "trend_summary": f"{symbol} is {trend}",
            "risk_flag": risk_flag,
            "reasoning": f"Based on RSI of {rsi:.2f} and volatility of {volatility:.2f}%, the stock shows {risk_flag} risk",
            "caveats": "This is a fallback analysis due to LLM unavailability. Please consult other sources.",
            "technical_outlook": f"RSI is {'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'}",
            "confidence_score": 0.3
        }
