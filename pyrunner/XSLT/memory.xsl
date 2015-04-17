<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0">
    <xsl:output type="html" encoding="UTF-8" indent="yes" />

    <xsl:template match="/">
        <html>
            <body>
                <xsl:apply-templates select="pyrunner/benchmark" />
            </body>
        </html>
    </xsl:template>
    
    <xsl:template match="benchmark">
        <h2><xsl:value-of select="@id" /></h2>
        
        <table>
            <tr>
                <th>Testcase</th>
                <xsl:apply-templates select="testcase[1]/command/@id" modes="TableHeader" />
            </tr>
            <xsl:apply-templates select="testcase" />
        </table>
    </xsl:template>

    <xsl:template match="command/@id" modes="TableHeader">
        <th><xsl:value-of select="." /></th>
    </xsl:template>
    
    <xsl:template match="testcase">
        <tr>
            <td><xsl:value-of select="@id" /></td>
            <xsl:apply-templates select="command/*" modes="TableData" />
        </tr>
    </xsl:template>
    
    <xsl:template match="command/pyrunlim" modes="TableData">
        <xsl:choose>
            <xsl:when test="stats/@status = 'complete'">
                <td>
                    <xsl:value-of select="format-number(stats/@time, '0.0 s / ')" />
                    <xsl:value-of select="format-number(stats/@memory, '0.0 MB')" />
                </td>
            </xsl:when>
            <xsl:when test="stats/@status = 'out of time'">
                <td>
                    ><xsl:value-of select="@time-limit" /> s /
                    <xsl:value-of select="format-number(stats/@memory, '0.0 MB')" />
                </td>
            </xsl:when>
            <xsl:when test="stats/@status = 'out of memory'">
                <td>
                    <xsl:value-of select="format-number(stats/@time, '0.0 s / ')" />
                    ><xsl:value-of select="@memory-limit" /> MB
                </td>
            </xsl:when>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="command/skip" modes="TableData">
        <td>skip</td>
    </xsl:template>    
</xsl:stylesheet>
